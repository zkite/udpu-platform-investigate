package main

import (
	"context"
	"flag"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"

	"udpuClient/constants"
	"udpuClient/ctx"
	"udpuClient/database"
	"udpuClient/global"
	"udpuClient/logx"
	"udpuClient/process"
	"udpuClient/response"
	"udpuClient/rest"
	"udpuClient/types"
	"udpuClient/utils"
	"udpuClient/wg"
	"udpuClient/ws"
)

var (
	// Secret material and state flags.
	secretKey   string
	hadExisting bool

	// Flag read from CLI. Global for parity with original layout.
	debugEnabled bool
)

// NewConfig builds configuration from flags. Signatures are unchanged by design.
func NewConfig() *types.Config {
	// Create empty config.
	cfg := &types.Config{}

	// Define CLI flags.
	flag.StringVar(&cfg.DiscoveryHost, "discovery-host", "", "The discovery server host (required)")
	flag.IntVar(&cfg.DiscoveryPort, "discovery-port", 0, "The discovery server port (required)")
	flag.StringVar(&cfg.DownloadPath, "download-path", constants.DefaultDownloadPath, "The directory for the downloaded software")
	flag.StringVar(&cfg.MacInterface, "mac-interface", constants.DefaultMacInterface, "MAC address interface")
	flag.BoolVar(&cfg.LocalTest, "local-test", false, "Enable local testing mode with predefined MAC and server host/port")
	flag.BoolVar(&debugEnabled, "debug", false, "Enable debug logging")

	// Parse flags.
	flag.Parse()

	// Validate required flags.
	if cfg.DiscoveryHost == "" || cfg.DiscoveryPort == 0 {
		logx.Fatalf("discovery-host and discovery-port are required parameters")
	}

	// Apply debug flag to global logger.
	logx.SetDebug(debugEnabled)

	return cfg
}

func main() {
	// Root context for coordinated shutdown.
	appCtx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// OS signal handling for graceful shutdown.
	shutdownChan := make(chan os.Signal, 1)
	signal.Notify(shutdownChan, os.Interrupt, syscall.SIGTERM)
	defer signal.Stop(shutdownChan)
	go func() {
		<-shutdownChan
		logx.Infof("Received shutdown signal. Starting graceful shutdown...")
		cancel()
	}()

	// Config and global paths.
	cfg := NewConfig()
	*global.SoftwarePath = cfg.DownloadPath
	*global.MacInterface = cfg.MacInterface

	// Database initialization.
	database.InitDatabase("")
	if err := database.CreateTables(); err != nil {
		logx.Fatalf("%v", err)
	}

	// Secret handling: JSON for local-test, U-Boot env in production.
	if cfg.LocalTest {
		if k, ok := database.GetClientSecretKey(); ok {
			secretKey, hadExisting = k, true
		} else {
			secretKey = utils.GenerateRandomHash()
			if err := database.SetClientSecretKey(secretKey); err != nil {
				logx.Infof("Error saving local test secret to JSON: %v", err)
			}
			hadExisting = false
		}
	} else {
		if k, err := utils.GetFwEnv(constants.SecretEnv); err == nil && k != "" {
			secretKey, hadExisting = k, true
		} else {
			secretKey = utils.GenerateRandomHash()
			if err := utils.SetFwEnv(constants.SecretEnv, secretKey); err != nil {
				logx.Infof("Error setting %s: %v", constants.SecretEnv, err)
			}
			hadExisting = false
		}
	}

	// Local test overrides for server and repo endpoints.
	if cfg.LocalTest {
		logx.Infof("Local testing mode enabled. Overriding server and repo host/port and MAC address")
		*global.ServerHost = constants.LocalTestServerHost
		*global.ServerPort = constants.LocalTestServerPort
		*global.RepoHost = constants.LocalTestRepoHost
		*global.RepoPort = constants.LocalTestRepoPort
	}

	// Detect outbound IP.
	ip, err := utils.GetOutboundIP()
	if err != nil {
		logx.Fatalf("Failed to get outbound IP address: %v", err)
	}
	ctx.SetDeviceIP(ip.String())
	logx.Infof("Outbound IP address: %s", ctx.GetDeviceIP())

	// Detect MAC.
	var mac string
	if cfg.LocalTest {
		if v := strings.TrimSpace(os.Getenv("LOCAL_TEST_MAC")); v != "" {
			mac = v
			logx.Debugf("Local testing mode: using MAC from env LOCAL_TEST_MAC=%s", mac)
		} else {
			mac = constants.LocalTestMAC
			logx.Debugf("Local testing mode: env LOCAL_TEST_MAC is empty or unset. Using default MAC %s", mac)
		}
	} else {
		mac, err = utils.GetMACAddress()
		if err != nil {
			logx.Fatalf("Error obtaining MAC address: %v", err)
		}
		logx.Infof("MAC address: %s", mac)
	}

	// Service discovery when not in local-test.
	if !cfg.LocalTest {
		*global.ServerHost, *global.ServerPort = rest.DiscoverService(appCtx, cfg.DiscoveryHost, cfg.DiscoveryPort, "server")
		logx.Infof("Discovered server: %s:%d", *global.ServerHost, *global.ServerPort)

		*global.RepoHost, *global.RepoPort = rest.DiscoverService(appCtx, cfg.DiscoveryHost, cfg.DiscoveryPort, "repo")
		logx.Infof("Discovered repo: %s:%d", *global.RepoHost, *global.RepoPort)
	} else {
		logx.Infof("Local testing mode: using server %s:%d", *global.ServerHost, *global.ServerPort)
		logx.Infof("Local testing mode: using repo %s:%d", *global.RepoHost, *global.RepoPort)
	}

	// Generate device stamp.
	udpuStamp := utils.GenerateSecret(mac, secretKey)
	if !hadExisting {
		// First boot: send stamp to server.
		data := types.StampData{
			MACAddress: mac,
			Body:       udpuStamp,
		}
		stampsURL := rest.CreateURL("http", nil, "stamps")
		if err := rest.SendStampData(stampsURL, data); err != nil {
			logx.Infof("Cannot send stamp: %v", err)
		}
	} else {
		// Existing secret: verify server-side stamp for MAC.
		stampsURLWithMAC := rest.CreateURL("http", nil, "stamps", mac)
		fetched, err := rest.FetchStamp(stampsURLWithMAC)
		if err != nil {
			logx.Infof("Cannot fetch stamp: %v", err)
		}
		if fetched != udpuStamp {
			logx.Infof("Duplicate MAC address error")
			cancel()
			<-appCtx.Done()
			return
		}
	}

	// Wait for server data.
	respObj, err := rest.WaitForData(appCtx, mac)
	if err != nil {
		logx.Fatalf("Failed to get server data: %v", err)
	}

	if err := database.UpdateOrCreateClientName(respObj.SubscriberUID); err != nil {
		logx.Infof("Failed to persist subscriber UID %s: %v", respObj.SubscriberUID, err)
	}

	var respAtomic atomic.Pointer[response.ServerResponse]
	respAtomic.Store(respObj)

	var registeredRuntimeOnce sync.Once
	startRegisteredRuntime := func(cur *response.ServerResponse) {
		if cur == nil {
			return
		}

		registeredRuntimeOnce.Do(func() {
			if err := database.UpdateOrCreateClientName(cur.SubscriberUID); err != nil {
				logx.Infof("Failed to persist subscriber UID %s: %v", cur.SubscriberUID, err)
			}

			if err := wg.SetupWG(cur); err != nil {
				logx.Infof("Failed to setup WireGuard tunnel: %v", err)
			} else if ipPart, _, err := net.ParseCIDR(cur.WGServerIP); err == nil {
				*global.ServerHost = ipPart.String()
				logx.Debugf("Server host overridden by WG IP: %s", *global.ServerHost)
			}

			ws.InitWS(cur.SubscriberUID)
			go func(uid string) {
				for {
					if err := ws.ListenWS(); err != nil {
						logx.Infof("WebSocket listen error: %v. Reconnecting in %s...", err, constants.WSReconnectDelay)
					}
					select {
					case <-appCtx.Done():
						logx.Infof("Shutting down WebSocket listener")
						return
					case <-time.After(constants.WSReconnectDelay):
						ws.InitWS(uid)
					}
				}
			}(cur.SubscriberUID)

			rest.StartUdpuStatusLoop(cur.SubscriberUID)
			process.ProcessUdpuData(cur)
		})
	}

	if cur := respAtomic.Load(); cur != nil && cur.MacAddress == constants.ZeroMAC {
		logx.Infof("Polling by MAC %s every 5s (non-blocking)", mac)

		go func() {
			t := time.NewTicker(5 * time.Second)
			defer t.Stop()
			for {
				select {
				case <-appCtx.Done():
					return
				case <-t.C:
					upd, err := rest.GetUdpuDataByMac(mac)
					if err != nil {
						continue
					}

					respAtomic.Store(&upd)
					if err := database.UpdateOrCreateClientName(upd.SubscriberUID); err != nil {
						logx.Infof("Failed to persist subscriber UID %s: %v", upd.SubscriberUID, err)
					}

					if upd.MacAddress != constants.ZeroMAC {
						logx.Infof("Resolved non-placeholder MAC: %s", upd.MacAddress)
						startRegisteredRuntime(&upd)
						return
					}
				}
			}
		}()
	} else {
		startRegisteredRuntime(respAtomic.Load())
	}

	defer func() {
		if global.WSConn != nil {
			logx.Debugf("Closing WebSocket connection")
			global.WSConn.Close()
		}
	}()

	// Periodic sender for unregistered devices.
	go func() {
		ticker := time.NewTicker(constants.UnregisteredTickInterval)
		defer ticker.Stop()
		var sendingMu sync.Mutex

		for {
			select {
			case <-appCtx.Done():
				logx.Infof("Shutting down unregistered device sender")
				return
			case <-ticker.C:
				if unreg := ctx.IsUnregisteredDevice(); unreg && sendingMu.TryLock() {
					go func() {
						defer sendingMu.Unlock()
						if cur := respAtomic.Load(); cur != nil {
							rest.SendUnregisteredDevice(cur.SubscriberUID, ctx.GetDeviceIP())
						}
						logx.Debugf("Sent unregistered device status")
					}()
				}
			}
		}
	}()

	// Block until context cancellation.
	<-appCtx.Done()
	logx.Infof("Exiting main function gracefully...")
}

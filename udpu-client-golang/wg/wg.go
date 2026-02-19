package wg

import (
	"fmt"
	"io"
	"net"
	"net/http"
	"os/exec"
	"strings"
	"time"

	"udpuClient/logx"
	"udpuClient/response"
	"udpuClient/rest"
	"udpuClient/utils"

	"golang.zx2c4.com/wireguard/wgctrl"
	"golang.zx2c4.com/wireguard/wgctrl/wgtypes"
)

// ptrDuration returns a pointer to a duration value.
func ptrDuration(d time.Duration) *time.Duration { return &d }

// SetupWG configures a WireGuard interface according to server response.
func SetupWG(resp *response.ServerResponse) error {
	// Nothing to do if no client IP is provided.
	if resp.WGClientIP == "" {
		return nil
	}

	// Interface name, default to wg0.
	ifaceName := resp.WGInterface
	if ifaceName == "" {
		ifaceName = "wg0"
	}

	// Recreate interface from scratch.
	_ = exec.Command("ip", "link", "del", ifaceName).Run()
	if err := exec.Command("ip", "link", "add", ifaceName, "type", "wireguard").Run(); err != nil {
		return err
	}

	// Assign client address.
	if err := exec.Command("ip", "address", "replace", resp.WGClientIP, "dev", ifaceName).Run(); err != nil {
		return err
	}

	// Bring interface up.
	if err := exec.Command("ip", "link", "set", "up", "dev", ifaceName).Run(); err != nil {
		return err
	}

	// WireGuard netlink client.
	client, err := wgctrl.New()
	if err != nil {
		return err
	}
	defer client.Close()

	// Parse server public key.
	peerPubKey, err := wgtypes.ParseKey(resp.WGServerPublicKey)
	if err != nil {
		return err
	}

	// Load or generate local private key.
	myPrivateKey, err := utils.LoadOrGeneratePrivateKey("WG_PRIVATE_KEY")
	if err != nil {
		return fmt.Errorf("WireGuard private key setup failed: %w", err)
	}

	// Build server CIDR from server IP (single host /32 or /128).
	ipPart, _, err := net.ParseCIDR(resp.WGServerIP)
	if err != nil {
		return err
	}
	serverMask := 32
	if ipPart.To4() == nil {
		serverMask = 128
	}
	serverCIDR := net.IPNet{IP: ipPart, Mask: net.CIDRMask(serverMask, serverMask)}

	// AllowedIPs starts with server host route.
	allowedIPs := []net.IPNet{serverCIDR}

	// Add extra routes from WGRoutes, deduplicated.
	seen := make(map[string]struct{})
	for _, tok := range strings.Split(resp.WGRoutes, ",") {
		s := strings.TrimSpace(tok)
		if s == "" {
			continue
		}
		if strings.Contains(s, "/") {
			_, n, err := net.ParseCIDR(s)
			if err != nil {
				return fmt.Errorf("invalid CIDR %q: %w", s, err)
			}
			k := n.String()
			if _, ok := seen[k]; ok {
				continue
			}
			seen[k] = struct{}{}
			allowedIPs = append(allowedIPs, *n)
		} else {
			ip := net.ParseIP(s)
			if ip == nil {
				return fmt.Errorf("invalid IP %q", s)
			}
			mask := 32
			if ip.To4() == nil {
				mask = 128
			}
			n := net.IPNet{IP: ip, Mask: net.CIDRMask(mask, mask)}
			k := n.String()
			if _, ok := seen[k]; ok {
				continue
			}
			seen[k] = struct{}{}
			allowedIPs = append(allowedIPs, n)
		}
	}

	// Resolve server endpoint.
	endpointStr := net.JoinHostPort(resp.Endpoint, fmt.Sprint(resp.WGServerPort))
	endpoint, err := net.ResolveUDPAddr("udp", endpointStr)
	if err != nil {
		return err
	}

	// Apply WG config: private key and peer config.
	cfg := wgtypes.Config{
		PrivateKey:   &myPrivateKey,
		ReplacePeers: true,
		Peers: []wgtypes.PeerConfig{{
			PublicKey:                   peerPubKey,
			Endpoint:                    endpoint,
			AllowedIPs:                  allowedIPs,
			PersistentKeepaliveInterval: ptrDuration(25 * time.Second),
		}},
	}
	if err := client.ConfigureDevice(ifaceName, cfg); err != nil {
		return err
	}

	// Install routes for AllowedIPs via the WG interface.
	for _, ipnet := range allowedIPs {
		if err := exec.Command("ip", "route", "replace", ipnet.String(), "dev", ifaceName).Run(); err != nil {
			return fmt.Errorf("failed to add route %s: %w", ipnet.String(), err)
		}
	}

	// Register our public key on the server.
	myPublicKey := myPrivateKey.PublicKey().String()
	peerAddURL := rest.CreateURL("http", nil, "wireguard", "peer", "add")
	payload := map[string]interface{}{
		"public_key":  myPublicKey,
		"allowed_ips": []string{resp.WGClientIP},
	}

	logx.Infof("Registering WireGuard peer at %s", peerAddURL)
	respPeer, err := rest.SendJSONRequest(peerAddURL, payload)
	if err != nil {
		return err
	}
	defer respPeer.Body.Close()
	if respPeer.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(respPeer.Body)
		return fmt.Errorf("failed to add peer: %s", string(bodyBytes))
	}

	logx.Infof("WireGuard setup complete on %s", ifaceName)
	return nil
}

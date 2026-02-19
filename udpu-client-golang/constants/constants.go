package constants

import "time"

// Secret key env var name used by fw_setenv/fw_printenv
const SecretEnv = "UDPU_SECRET_KEY"

// Public API version for server communication
const APIVersion = "v1.0"

// Defaults and tuning knobs extracted from main.
const (
	DefaultDownloadPath = "/tmp"   // Default directory for downloads
	DefaultMacInterface = "br-lan" // Default MAC interface for production

	LocalTestServerHost = "host.docker.internal" // Local test server host
	LocalTestRepoHost   = "host.docker.internal" // Local test repo host

	LocalTestServerPort = 8888 // Local test server port
	LocalTestRepoPort   = 8887 // Local test repo port

	LocalTestMAC = "00:11:22:33:44:55" // Deterministic MAC for local testing
	ZeroMAC      = "00:00:00:00:00:00"

	EveryBoot = "every_boot"

	// client boot status
	BootStatusFirst   = "first_boot"
	BootStatusRegular = "every_boot"
)

// Timing constants used across the app.
const (
	UnregisteredTickInterval = 5 * time.Second // Interval for sending unregistered device pings
	WSReconnectDelay         = 5 * time.Second // Delay before WS reconnect attempt
)

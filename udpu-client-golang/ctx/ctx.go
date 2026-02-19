package ctx

import (
	"sync"
)

// AppState holds runtime flags and device IP.
// Access is guarded by mu to ensure thread safety.
var AppState = struct {
	isUnregisteredDevice bool
	deviceIP             string
	mu                   sync.Mutex
}{}

// SetUnregisteredDevice sets the registration flag.
func SetUnregisteredDevice(v bool) {
	AppState.mu.Lock()
	AppState.isUnregisteredDevice = v
	AppState.mu.Unlock()
}

// IsUnregisteredDevice reports whether the device is unregistered.
func IsUnregisteredDevice() bool {
	AppState.mu.Lock()
	defer AppState.mu.Unlock()
	return AppState.isUnregisteredDevice
}

// SetDeviceIP updates the cached device IP address.
func SetDeviceIP(ip string) {
	AppState.mu.Lock()
	AppState.deviceIP = ip
	AppState.mu.Unlock()
}

// GetDeviceIP returns the cached device IP address.
func GetDeviceIP() string {
	AppState.mu.Lock()
	defer AppState.mu.Unlock()
	return AppState.deviceIP
}

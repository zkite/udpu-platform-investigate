package utils

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"net"
	"os/exec"
	"strings"

	"udpuClient/database"
	"udpuClient/global"
	"udpuClient/logx"

	"golang.zx2c4.com/wireguard/wgctrl/wgtypes"
)

// GetFwEnv reads a U-Boot environment value via fw_printenv.
func GetFwEnv(key string) (string, error) {
	output, err := exec.Command("fw_printenv", key).CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("fw_printenv error for %s: %w, output: %q", key, err, string(output))
	}
	parts := strings.SplitN(string(output), "=", 2)
	if len(parts) < 2 {
		return "", fmt.Errorf("value for '%s' not found in fw_printenv output", key)
	}
	return strings.TrimSpace(parts[1]), nil
}

// SetFwEnv writes a U-Boot environment value via fw_setenv.
func SetFwEnv(key, value string) error {
	out, err := exec.Command("fw_setenv", key, value).CombinedOutput()
	if err != nil {
		return fmt.Errorf("fw_setenv error for %s=%s: %w, output: %q", key, value, err, string(out))
	}
	return nil
}

// LoadOrGeneratePrivateKey loads a WireGuard private key from env or generates and saves a new one.
func LoadOrGeneratePrivateKey(envKeyName string) (wgtypes.Key, error) {
	keyStr, err := GetFwEnv(envKeyName)
	if err == nil && keyStr != "" {
		key, parseErr := wgtypes.ParseKey(keyStr)
		if parseErr == nil {
			return key, nil
		}
	}
	newKey, err := wgtypes.GeneratePrivateKey()
	if err != nil {
		return wgtypes.Key{}, fmt.Errorf("failed to generate WireGuard key: %w", err)
	}
	if err := SetFwEnv(envKeyName, newKey.String()); err != nil {
		return wgtypes.Key{}, fmt.Errorf("failed to save WireGuard key: %w", err)
	}
	return newKey, nil
}

// GenerateSecret creates a SHA-256 hex digest of mac+secret.
func GenerateSecret(mac, secret string) string {
	combined := mac + secret
	hasher := sha256.New()
	hasher.Write([]byte(combined))
	return hex.EncodeToString(hasher.Sum(nil))
}

// GenerateRandomHash returns a random 32-byte SHA-256 hex string.
func GenerateRandomHash() string {
	randomBytes := make([]byte, 32)
	if _, err := rand.Read(randomBytes); err != nil {
		logx.Infof("Error generating random bytes: %v", err)
	}
	hasher := sha256.New()
	hasher.Write(randomBytes)
	return hex.EncodeToString(hasher.Sum(nil))
}

// GetOutboundIP determines the preferred outbound IP by opening a UDP socket.
func GetOutboundIP() (net.IP, error) {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	localAddr := conn.LocalAddr().(*net.UDPAddr)
	return localAddr.IP, nil
}

// GetMACAddress returns the MAC of the configured interface.
func GetMACAddress() (string, error) {
	interfaces, err := net.Interfaces()
	if err != nil {
		return "", err
	}
	for _, interf := range interfaces {
		if interf.Name == *global.MacInterface {
			if len(interf.HardwareAddr) > 0 {
				return interf.HardwareAddr.String(), nil
			}
			return "", errors.New("MAC address for interface not found")
		}
	}
	return "", errors.New("Interface not found")
}

// GetClientSubscriberId returns the current client subscriber ID or "none".
func GetClientSubscriberId() string {
	client, err := database.GetClient()
	if err != nil || client == nil || client.Name == "" {
		return "none"
	}
	return client.Name
}

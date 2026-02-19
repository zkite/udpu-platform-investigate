package rest

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path"
	"strconv"
	"strings"
	"time"

	"udpuClient/constants"
	"udpuClient/ctx"
	"udpuClient/discovery"
	"udpuClient/global"
	"udpuClient/logx"
	"udpuClient/response"
	"udpuClient/types"
	"udpuClient/utils"
)

// UnregisteredDevicePayload is sent for devices not yet registered.
type UnregisteredDevicePayload struct {
	SubscriberUID  string `json:"subscriber_uid"`
	LastCallHomeDT string `json:"last_call_home_dt"`
	IPAddress      string `json:"ip_address"`
}

// shared HTTP client with a sane timeout.
var globalHTTPClient = &http.Client{Timeout: 10 * time.Second}

// CreateURL builds service URLs like /api/vX/... with optional query.
func CreateURL(scheme string, params url.Values, segments ...string) string {
	parts := make([]string, 0, len(segments)+2)
	parts = append(parts, "api", constants.APIVersion)
	for _, s := range segments {
		parts = append(parts, url.PathEscape(s))
	}
	p := "/" + path.Join(parts...)

	u := url.URL{
		Scheme: scheme,
		Host:   net.JoinHostPort(*global.ServerHost, strconv.Itoa(*global.ServerPort)),
		Path:   p,
	}
	if params != nil {
		u.RawQuery = params.Encode()
	}
	return u.String()
}

// sendJSONRequest POSTs JSON to urlStr and returns the HTTP response.
func SendJSONRequest(urlStr string, data interface{}) (*http.Response, error) {
	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}

	//logx.Infof("Sending POST %s payload: %s", urlStr, string(jsonData))

	req, err := http.NewRequest("POST", urlStr, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	return globalHTTPClient.Do(req)
}

// SendUdpuStatus posts uDPU status heartbeat.
func SendUdpuStatus(subscriberUID, state, status string) {
	data := map[string]string{
		"subscriber_uid": subscriberUID,
		"state":          state,
		"status":         status,
	}

	urlStr := CreateURL("http", nil, "udpu", "status")
	resp, err := SendJSONRequest(urlStr, data)
	if err != nil {
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		logx.Infof("Received non-200 response for udpu/status: %s", resp.Status)
	}
}

// StartUdpuStatusLoop sends status every 5 seconds in a goroutine.
func StartUdpuStatusLoop(subscriberUID string) {
	go func() {
		for {
			SendUdpuStatus(subscriberUID, "", "online")
			time.Sleep(5 * time.Second)
		}
	}()
}

// SendUnregisteredDevice notifies server about an unregistered device.
func SendUnregisteredDevice(subscriberUID, ip string) {
	data := UnregisteredDevicePayload{
		SubscriberUID:  subscriberUID,
		LastCallHomeDT: time.Now().Format(time.RFC3339),
		IPAddress:      ip,
	}

	urlStr := CreateURL("http", nil, "unregistered_device")
	resp, err := SendJSONRequest(urlStr, data)
	if err != nil {
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logx.Infof("Received non-200 response for unregistered_device: %s", resp.Status)
	}
}

// SendStampData posts the device stamp.
func SendStampData(urlStr string, data types.StampData) error {
	resp, err := SendJSONRequest(urlStr, data)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusForbidden {
		logx.Infof("Duplicate MAC address error")
		os.Exit(1)
	}
	logx.Infof("Stamp POST response: %s", resp.Status)
	return nil
}

// FetchStamp gets a stamp body string from server.
func FetchStamp(urlStr string) (string, error) {
	resp, err := http.Get(urlStr)
	if err != nil {
		return "", fmt.Errorf("Request error: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("Server response status: %s", resp.Status)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("Error reading response body: %w", err)
	}

	var data map[string]string
	if err := json.Unmarshal(body, &data); err != nil {
		return "", fmt.Errorf("Error unmarshalling JSON: %w", err)
	}

	stamp, ok := data["body"]
	if !ok {
		return "", fmt.Errorf("Key 'body' does not exist")
	}

	return stamp, nil
}

// hasRealMAC reports whether MAC is real and sends status accordingly.
func hasRealMAC(resp response.ServerResponse) bool {
	m := strings.ToLower(strings.TrimSpace(resp.MacAddress))
	registered := m != "00:00:00:00:00:00"

	if registered {
		SendUdpuStatus(resp.SubscriberUID, "registered", "online")
	} else {
		SendUdpuStatus(resp.SubscriberUID, "not_registered", "online")
	}

	return registered
}

// GetUdpuDataByMac fetches uDPU payload by MAC and updates ctx registration state.
func GetUdpuDataByMac(macAddress string) (response.ServerResponse, error) {
	var respObj response.ServerResponse

	clientName := utils.GetClientSubscriberId()
	params := url.Values{}
	params.Set("subscriber", clientName)
	urlStr := CreateURL("http", params, "adapter", macAddress, "udpu")

	resp, err := http.Get(urlStr)
	if err != nil {
		ctx.SetUnregisteredDevice(true)
		return respObj, fmt.Errorf("http GET %s: %w", urlStr, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		ctx.SetUnregisteredDevice(true)
		return respObj, fmt.Errorf("unexpected HTTP status: %s", resp.Status)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return respObj, fmt.Errorf("read body: %w", err)
	}
	if err := json.Unmarshal(body, &respObj); err != nil {
		return respObj, fmt.Errorf("unmarshal body: %w", err)
	}

	registered := hasRealMAC(respObj)
	ctx.SetUnregisteredDevice(!registered)

	logx.Infof("uDPU payload: %s", string(body))
	return respObj, nil
}

// DiscoverService loops until it discovers a service or ctx is canceled.
func DiscoverService(ctx context.Context, discoveryHost string, discoveryPort int, serviceName string) (string, int) {
	for {
		host, port := discovery.Discovery(discoveryHost, discoveryPort, serviceName, 2)
		if host != "" {
			return host, port
		}
		logx.Infof("No %s discovered, retrying...", serviceName)
		select {
		case <-ctx.Done():
			return "", 0
		case <-time.After(5 * time.Second):
		}
	}
}

// WaitForData polls until data arrives or context is canceled.
func WaitForData(c context.Context, macAddress string) (*response.ServerResponse, error) {
	for {
		select {
		case <-c.Done():
			return nil, c.Err()
		default:
		}

		respObj, err := GetUdpuDataByMac(macAddress)
		if err == nil {
			return &respObj, nil
		}
		logx.Infof("Error making request: %v", err)

		select {
		case <-c.Done():
			return nil, c.Err()
		case <-time.After(5 * time.Second):
		}
	}
}

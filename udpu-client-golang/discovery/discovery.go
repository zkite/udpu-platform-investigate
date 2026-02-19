package discovery

import (
	"encoding/json"
	"io"
	"math"
	"net/http"
	"strconv"
	"time"

	"udpuClient/logx"
)

// Server represents a server's host and port.
type Server struct {
	Host        string `json:"host"`
	Port        string `json:"port"`
	ServiceType string `json:"service_type"`
}

// Discovery discovers a server with the minimum request time.
func Discovery(host string, port int, serviceType string, timeout time.Duration) (string, int) {
	// HTTP client with per-request timeout (seconds expected in timeout argument).
	client := &http.Client{Timeout: timeout * time.Second}

	// Build URL of the discovery endpoint.
	serviceURL := "http://" + host + ":" + strconv.Itoa(port) + "/api/v1.0/services"
	logx.Infof("Requesting server list from: %s", serviceURL)

	// Create GET request for the service list.
	req, err := http.NewRequest("GET", serviceURL, nil)
	if err != nil {
		logx.Infof("Server discovery error: can't create request for %s", serviceType)
		return "", 0
	}

	// Add service_type query parameter.
	q := req.URL.Query()
	q.Add("service_type", serviceType)
	req.URL.RawQuery = q.Encode()

	logx.Infof("Making request to URL: %s", req.URL.String())

	// Perform the HTTP request.
	resp, err := client.Do(req)
	if err != nil {
		logx.Infof("Server discovery error: can't get list of servers for %s", serviceType)
		return "", 0
	}
	defer resp.Body.Close()

	// Read the response body.
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logx.Infof("Error reading response body: %v", err)
		return "", 0
	}

	logx.Infof("Discovery response body: %s", body)

	// Decode the list of servers.
	var servers []Server
	if err := json.Unmarshal(body, &servers); err != nil {
		logx.Infof("Error decoding server list for %s: %v", serviceType, err)
		return "", 0
	}

	// Pick server with minimal /health latency.
	var (
		serverHost      string
		serverPortInt   int
		minResponseTime = time.Duration(math.MaxInt64)
	)

	for _, server := range servers {
		// Convert port to int.
		portInt, err := strconv.Atoi(server.Port)
		if err != nil {
			logx.Infof("Error converting port for host %s: %v", server.Host, err)
			continue
		}

		// Health-check URL to measure latency.
		serverURL := "http://" + server.Host + ":" + server.Port + "/api/v1.0/health"
		start := time.Now()
		response, err := client.Get(serverURL)
		if err != nil {
			// Skip unreachable server.
			continue
		}
		response.Body.Close()

		// Compare and keep the best.
		responseTime := time.Since(start)
		if responseTime < minResponseTime {
			serverHost = server.Host
			serverPortInt = portInt
			minResponseTime = responseTime
			logx.Infof("Current best: %s, time: %s", serverHost, minResponseTime)
		}
	}

	// Report result and return selected host and port.
	if serverHost == "" {
		logx.Infof("Can't reach any %s or list of servers are empty", serviceType)
	} else {
		logx.Infof("Nearest %s: %s, time: %s", serviceType, serverHost, minResponseTime)
	}

	return serverHost, serverPortInt
}

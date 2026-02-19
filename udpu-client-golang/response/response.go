package response

type ServerResponse struct {
	SubscriberUID string `json:"subscriber_uid"`
	Location      string `json:"location"`
	MacAddress    string `json:"mac_address"`
	Role          string `json:"role"`
	UpstreamQoS   string `json:"upstream_qos"`
	DownstreamQoS string `json:"downstream_qos"`
	Hostname      string `json:"hostname"`

	// WireGuard configuration fields:
	WGServerPublicKey string `json:"wg_server_public_key"` // The server's WG public key.
	WGInterface       string `json:"wg_interface"`         // Typically "wg0".
	WGServerIP        string `json:"wg_server_ip"`         // Internal WG address of the server (e.g. "10.66.0.2/31").
	WGServerPort      string `json:"wg_server_port"`       // Server's listen port (e.g. "51820").
	WGClientIP        string `json:"wg_client_ip"`         // The address assigned to the client (e.g. "10.66.0.3/31").
	WGRoutes          string `json:"wg_routes"`            // Additional networks routed through the tunnel (e.g. "10.250/16,10.251/16").
	WGAllowedIPs      string `json:"wg_allowed_ips"`       // Allowed IPs for the tunnel (e.g. could be the client address or a range).
	Endpoint          string `json:"endpoint"`
}

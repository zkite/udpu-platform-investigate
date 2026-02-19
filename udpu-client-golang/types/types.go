package types

import (
	"udpuClient/response"
)

type StampData struct {
	MACAddress string `json:"mac_address"`
	Body       string `json:"body"`
}

type UdpuUpdate struct {
	UpstreamQoS   interface{}
	DownstreamQoS interface{}
	Hostname      interface{}
	Location      interface{}
	Role          interface{}
	BootStatus    interface{}
}

type PublicKeyResponse struct {
	PublicKey string `json:"public_key"`
}

type Config struct {
	DiscoveryHost string
	DiscoveryPort int
	DownloadPath  string
	MacInterface  string
	LocalTest     bool
}

func (u UdpuUpdate) ToMap() map[string]interface{} {
	return map[string]interface{}{
		"udpu_upstream_qos":   u.UpstreamQoS,
		"udpu_downstream_qos": u.DownstreamQoS,
		"udpu_hostname":       u.Hostname,
		"udpu_location":       u.Location,
		"udpu_role":           u.Role,
		"boot_status":         u.BootStatus,
	}
}

func NewUdpuUpdate(r *response.ServerResponse) UdpuUpdate {
	return UdpuUpdate{
		UpstreamQoS:   r.UpstreamQoS,
		DownstreamQoS: r.DownstreamQoS,
		Hostname:      r.Hostname,
		Location:      r.Location,
		Role:          r.Role,
		BootStatus:    "every_boot",
	}
}

type JobLog struct {
	Client     string `json:"client"`
	Name       string `json:"name"`
	Command    string `json:"command"`
	StdErr     string `json:"std_err"`
	StdOut     string `json:"std_out"`
	StatusCode string `json:"status_code"`
	Timestamp  string `json:"timestamp"`
}

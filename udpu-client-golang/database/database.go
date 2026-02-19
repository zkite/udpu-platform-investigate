package database

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"syscall"
	"time"

	"udpuClient/logx"
	"udpuClient/response"
)

// =============================
// JSON-backed storage
// File: udpu_config.json (next to the executable)
// Layout:
// {
//   "client": { ... },
//   "jobs":   { "<name>": { ... }, ... },
//   "queues": { "<name>": { ... }, ... }
// }
// =============================

// Client stores client-related metadata.
type Client struct {
	Name              string `json:"name"`
	ClientFrequency   string `json:"client_frequency"`
	BootStatus        string `json:"boot_status"`
	UdpuUpstreamQoS   string `json:"udpu_upstream_qos"`
	UdpuDownstreamQoS string `json:"udpu_downstream_qos"`
	UdpuHostname      string `json:"udpu_hostname"`
	UdpuLocation      string `json:"udpu_location"`
	UdpuRole          string `json:"udpu_role"`
	UdpuSecretKey     string `json:"udpu_secret_key"`
}

// Job represents a scheduled or ad-hoc task description.
type Job struct {
	Name             string `json:"name"`
	Command          string `json:"command"`
	Frequency        string `json:"frequency"`
	Locked           string `json:"locked"`
	RequireOutput    string `json:"require_output"`
	RequiredSoftware string `json:"required_software"`
	JobType          string `json:"job_type"`
	VbuserID         string `json:"vbuser_id"`
}

// Queue represents a queue configuration record.
type Queue struct {
	Name          string `json:"name"`
	Description   string `json:"description"`
	Queue         string `json:"queue"`
	Role          string `json:"role"`
	RequireOutput string `json:"require_output"`
	Frequency     string `json:"frequency"`
	Locked        string `json:"locked"`
}

// configFile mirrors the on-disk JSON structure.
type configFile struct {
	Client Client           `json:"client"`
	Jobs   map[string]Job   `json:"jobs"`
	Queues map[string]Queue `json:"queues"`
}

var (
	cfg     configFile
	cfgPath string
)

// ----- utilities -----

// configFilePath returns path to config file near the executable.
func configFilePath() string {
	exe, err := os.Executable()
	if err != nil {
		return "udpu_config.json"
	}
	if p, err := filepath.EvalSymlinks(exe); err == nil {
		exe = p
	}
	return filepath.Join(filepath.Dir(exe), "udpu_config.json")
}

// ensureMaps initializes internal maps if nil.
func ensureMaps() {
	if cfg.Jobs == nil {
		cfg.Jobs = make(map[string]Job)
	}
	if cfg.Queues == nil {
		cfg.Queues = make(map[string]Queue)
	}
}

// readJSON decodes JSON from file into v.
func readJSON(path string, v any) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	dec := json.NewDecoder(f)
	dec.DisallowUnknownFields()
	return dec.Decode(v)
}

// writeJSONAtomic writes JSON atomically with a file lock.
func writeJSONAtomic(path string, v any) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}

	lockf, err := os.OpenFile(path+".lock", os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return err
	}
	defer lockf.Close()
	if err := syscall.Flock(int(lockf.Fd()), syscall.LOCK_EX); err != nil {
		return err
	}
	defer syscall.Flock(int(lockf.Fd()), syscall.LOCK_UN)

	tmp, err := os.CreateTemp(dir, ".udpu-*.tmp")
	if err != nil {
		return err
	}
	enc := json.NewEncoder(tmp)
	enc.SetIndent("", "  ")
	if err := enc.Encode(v); err != nil {
		tmp.Close()
		_ = os.Remove(tmp.Name())
		return err
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		_ = os.Remove(tmp.Name())
		return err
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmp.Name())
		return err
	}
	if err := os.Rename(tmp.Name(), path); err != nil {
		_ = os.Remove(tmp.Name())
		return err
	}
	if d, err := os.Open(dir); err == nil {
		_ = d.Sync()
		_ = d.Close()
	}
	return nil
}

// save persists current cfg to disk.
func save() error {
	ensureMaps()
	return writeJSONAtomic(cfgPath, &cfg)
}

// loadOrInit loads cfg or initializes a fresh file.
func loadOrInit() error {
	_, err := os.Stat(cfgPath)
	if errors.Is(err, os.ErrNotExist) {
		cfg = configFile{
			Client: Client{},
			Jobs:   map[string]Job{},
			Queues: map[string]Queue{},
		}
		return save()
	}
	if err != nil {
		return err
	}
	if err := readJSON(cfgPath, &cfg); err != nil {
		_ = backupCorrupt(cfgPath)
		return err
	}
	ensureMaps()
	return nil
}

// backupCorrupt copies the corrupt file to a timestamped backup.
func backupCorrupt(path string) error {
	backup := fmt.Sprintf("%s.bak.%d", path, time.Now().Unix())
	src, err := os.Open(path)
	if err != nil {
		return err
	}
	defer src.Close()
	dst, err := os.Create(backup)
	if err != nil {
		return err
	}
	defer dst.Close()
	_, err = io.Copy(dst, src)
	return err
}

// structToMap converts a struct to a generic map view.
func structToMap(v any) map[string]interface{} {
	b, _ := json.Marshal(v)
	var m map[string]interface{}
	_ = json.Unmarshal(b, &m)
	return m
}

// =====================================
// Public API with original function names
// =====================================

// InitDatabase sets cfgPath and loads or initializes the store.
func InitDatabase(_ string) {
	cfgPath = configFilePath()
	if err := loadOrInit(); err != nil {
		logx.Fatalf("init json store: %v", err)
	}
}

// CreateTables ensures maps exist and persists them.
func CreateTables() error {
	ensureMaps()
	return save()
}

// InsertIntoClient writes server response fields into client section.
func InsertIntoClient(r *response.ServerResponse) error {
	cfg.Client = Client{
		Name:              r.SubscriberUID,
		ClientFrequency:   cfg.Client.ClientFrequency,
		BootStatus:        "first_boot",
		UdpuUpstreamQoS:   r.UpstreamQoS,
		UdpuDownstreamQoS: r.DownstreamQoS,
		UdpuHostname:      r.Hostname,
		UdpuLocation:      r.Location,
		UdpuRole:          r.Role,
		UdpuSecretKey:     cfg.Client.UdpuSecretKey, // keep existing key
	}
	return save()
}

// GetClient returns the client record if present.
func GetClient() (*Client, error) {
	if cfg.Client.Name == "" && cfg.Client.UdpuHostname == "" {
		return nil, errors.New("client not found")
	}
	c := cfg.Client
	return &c, nil
}

// GetData returns a slice for a table by name or nil if not found.
func GetData(table string, name string) interface{} {
	switch table {
	case "job":
		var out []Job
		if j, ok := cfg.Jobs[name]; ok {
			out = append(out, j)
		}
		if len(out) == 0 {
			return nil
		}
		return out
	case "queue":
		var out []Queue
		if q, ok := cfg.Queues[name]; ok {
			out = append(out, q)
		}
		if len(out) == 0 {
			return nil
		}
		return out
	case "client":
		var out []Client
		if cfg.Client.Name == name {
			out = append(out, cfg.Client)
		}
		if len(out) == 0 {
			return nil
		}
		return out
	default:
		return nil
	}
}

// CreateData inserts or updates a record then persists it.
func CreateData(table string, kwargs map[string]interface{}) {
	if len(kwargs) == 0 {
		return
	}
	switch table {
	case "job":
		v, ok := kwargs["name"]
		if !ok {
			logx.Infof("Can't create job: missing name")
			return
		}
		name := fmt.Sprint(v)
		if name == "" || name == "<nil>" {
			logx.Infof("Can't create job: empty name")
			return
		}
		j := cfg.Jobs[name]
		j.Name = name
		if v, ok := kwargs["command"]; ok {
			j.Command = fmt.Sprint(v)
		}
		if v, ok := kwargs["frequency"]; ok {
			j.Frequency = fmt.Sprint(v)
		}
		if v, ok := kwargs["locked"]; ok {
			j.Locked = fmt.Sprint(v)
		}
		if v, ok := kwargs["require_output"]; ok {
			j.RequireOutput = fmt.Sprint(v)
		}
		if v, ok := kwargs["required_software"]; ok {
			j.RequiredSoftware = fmt.Sprint(v)
		}
		if v, ok := kwargs["job_type"]; ok {
			j.JobType = fmt.Sprint(v)
		}
		if v, ok := kwargs["vbuser_id"]; ok {
			j.VbuserID = fmt.Sprint(v)
		}
		cfg.Jobs[name] = j

	case "queue":
		v, ok := kwargs["name"]
		if !ok {
			logx.Infof("Can't create queue: missing name")
			return
		}
		name := fmt.Sprint(v)
		if name == "" || name == "<nil>" {
			logx.Infof("Can't create queue: empty name")
			return
		}
		q := cfg.Queues[name]
		q.Name = name
		if v, ok := kwargs["description"]; ok {
			q.Description = fmt.Sprint(v)
		}
		if v, ok := kwargs["queue"]; ok {
			q.Queue = fmt.Sprint(v)
		}
		if v, ok := kwargs["role"]; ok {
			q.Role = fmt.Sprint(v)
		}
		if v, ok := kwargs["require_output"]; ok {
			q.RequireOutput = fmt.Sprint(v)
		}
		if v, ok := kwargs["frequency"]; ok {
			q.Frequency = fmt.Sprint(v)
		}
		if v, ok := kwargs["locked"]; ok {
			q.Locked = fmt.Sprint(v)
		}
		cfg.Queues[name] = q

	case "client":
		if v, ok := kwargs["name"]; ok {
			cfg.Client.Name = fmt.Sprint(v)
		}
		if v, ok := kwargs["client_frequency"]; ok {
			cfg.Client.ClientFrequency = fmt.Sprint(v)
		}
		if v, ok := kwargs["boot_status"]; ok {
			cfg.Client.BootStatus = fmt.Sprint(v)
		}
		if v, ok := kwargs["udpu_upstream_qos"]; ok {
			cfg.Client.UdpuUpstreamQoS = fmt.Sprint(v)
		}
		if v, ok := kwargs["udpu_downstream_qos"]; ok {
			cfg.Client.UdpuDownstreamQoS = fmt.Sprint(v)
		}
		if v, ok := kwargs["udpu_hostname"]; ok {
			cfg.Client.UdpuHostname = fmt.Sprint(v)
		}
		if v, ok := kwargs["udpu_location"]; ok {
			cfg.Client.UdpuLocation = fmt.Sprint(v)
		}
		if v, ok := kwargs["udpu_role"]; ok {
			cfg.Client.UdpuRole = fmt.Sprint(v)
		}
		if v, ok := kwargs["udpu_secret_key"]; ok {
			cfg.Client.UdpuSecretKey = fmt.Sprint(v)
		}
	default:
		return
	}
	if err := save(); err != nil {
		logx.Infof("Can't create %s data: %v", table, err)
	}
}

// UpdateData updates an existing record then persists it.
func UpdateData(table string, name string, fields map[string]interface{}) {
	if len(fields) == 0 {
		return
	}
	switch table {
	case "job":
		j, ok := cfg.Jobs[name]
		if !ok {
			logx.Infof("Can't update job %q: not found", name)
			return
		}
		if v, ok := fields["command"]; ok {
			j.Command = fmt.Sprint(v)
		}
		if v, ok := fields["frequency"]; ok {
			j.Frequency = fmt.Sprint(v)
		}
		if v, ok := fields["locked"]; ok {
			j.Locked = fmt.Sprint(v)
		}
		if v, ok := fields["require_output"]; ok {
			j.RequireOutput = fmt.Sprint(v)
		}
		if v, ok := fields["required_software"]; ok {
			j.RequiredSoftware = fmt.Sprint(v)
		}
		if v, ok := fields["job_type"]; ok {
			j.JobType = fmt.Sprint(v)
		}
		if v, ok := fields["vbuser_id"]; ok {
			j.VbuserID = fmt.Sprint(v)
		}
		cfg.Jobs[name] = j

	case "queue":
		q, ok := cfg.Queues[name]
		if !ok {
			logx.Infof("Can't update queue %q: not found", name)
			return
		}
		if v, ok := fields["description"]; ok {
			q.Description = fmt.Sprint(v)
		}
		if v, ok := fields["queue"]; ok {
			q.Queue = fmt.Sprint(v)
		}
		if v, ok := fields["role"]; ok {
			q.Role = fmt.Sprint(v)
		}
		if v, ok := fields["require_output"]; ok {
			q.RequireOutput = fmt.Sprint(v)
		}
		if v, ok := fields["frequency"]; ok {
			q.Frequency = fmt.Sprint(v)
		}
		if v, ok := fields["locked"]; ok {
			q.Locked = fmt.Sprint(v)
		}
		cfg.Queues[name] = q

	case "client":
		if v, ok := fields["name"]; ok {
			cfg.Client.Name = fmt.Sprint(v)
		}
		if v, ok := fields["client_frequency"]; ok {
			cfg.Client.ClientFrequency = fmt.Sprint(v)
		}
		if v, ok := fields["boot_status"]; ok {
			cfg.Client.BootStatus = fmt.Sprint(v)
		}
		if v, ok := fields["udpu_upstream_qos"]; ok {
			cfg.Client.UdpuUpstreamQoS = fmt.Sprint(v)
		}
		if v, ok := fields["udpu_downstream_qos"]; ok {
			cfg.Client.UdpuDownstreamQoS = fmt.Sprint(v)
		}
		if v, ok := fields["udpu_hostname"]; ok {
			cfg.Client.UdpuHostname = fmt.Sprint(v)
		}
		if v, ok := fields["udpu_location"]; ok {
			cfg.Client.UdpuLocation = fmt.Sprint(v)
		}
		if v, ok := fields["udpu_role"]; ok {
			cfg.Client.UdpuRole = fmt.Sprint(v)
		}
		if v, ok := fields["udpu_secret_key"]; ok {
			cfg.Client.UdpuSecretKey = fmt.Sprint(v)
		}
	default:
		return
	}
	if err := save(); err != nil {
		logx.Infof("Can't update %s with data: %v", table, err)
	}
}

// DeleteData removes a record and persists the change.
func DeleteData(table string, name string) {
	switch table {
	case "job":
		if _, ok := cfg.Jobs[name]; ok {
			delete(cfg.Jobs, name)
		} else {
			logx.Infof("Can't delete job: %s not found", name)
		}
	case "queue":
		if _, ok := cfg.Queues[name]; ok {
			delete(cfg.Queues, name)
		} else {
			logx.Infof("Can't delete queue: %s not found", name)
		}
	case "client":
		if cfg.Client.Name == name {
			cfg.Client = Client{}
		} else {
			logx.Infof("Can't delete client: %s not found", name)
		}
	default:
		logx.Infof("Can't delete %s: unsupported table", table)
		return
	}
	if err := save(); err != nil {
		logx.Infof("Can't persist delete for %s: %s, error: %v", table, name, err)
	}
}

// GetWithFrequency filters records by frequency or scheduled flag.
func GetWithFrequency(table string, frequency string, scheduled bool) []map[string]interface{} {
	var out []map[string]interface{}
	switch table {
	case "job":
		for _, j := range cfg.Jobs {
			if scheduled {
				if j.Frequency == "1" || j.Frequency == "15" || j.Frequency == "60" || j.Frequency == "1440" {
					out = append(out, structToMap(j))
				}
			} else if j.Frequency == frequency {
				out = append(out, structToMap(j))
			}
		}
	case "queue":
		for _, q := range cfg.Queues {
			if scheduled {
				if q.Frequency == "1" || q.Frequency == "15" || q.Frequency == "60" || q.Frequency == "1440" {
					out = append(out, structToMap(q))
				}
			} else if q.Frequency == frequency {
				out = append(out, structToMap(q))
			}
		}
	default:
		logx.Infof("Table should be either job or queue")
		return nil
	}
	if len(out) == 0 {
		return nil
	}
	return out
}

// GetScheduled returns all scheduled jobs or queues by table.
func GetScheduled(table string) []map[string]interface{} {
	return GetWithFrequency(table, "", true)
}

// GetEveryBootJobs returns jobs with 'every_boot' frequency.
func GetEveryBootJobs() []map[string]interface{} {
	res := GetWithFrequency("job", "every_boot", false)
	if res == nil {
		logx.Infof("No jobs found with 'every_boot' frequency")
	}
	return res
}

// GetFirstBootJobs returns jobs with 'first_boot' frequency.
func GetFirstBootJobs() []map[string]interface{} {
	res := GetWithFrequency("job", "first_boot", false)
	if res == nil {
		logx.Infof("Can't get job's data with 'first_boot' frequency")
	}
	return res
}

// getJobOnce returns jobs with 'once' frequency.
func getJobOnce() []map[string]interface{} {
	res := GetWithFrequency("job", "once", false)
	if res == nil {
		logx.Infof("Can't get job's data with 'once' frequency")
	}
	return res
}

// GetJobsScheduled returns scheduled jobs.
func GetJobsScheduled() []map[string]interface{} {
	res := GetScheduled("job")
	if res == nil {
		logx.Infof("No scheduled jobs were found")
	}
	return res
}

// UpdateOrCreateClientName sets or updates the client name and persists it.
func UpdateOrCreateClientName(newName string) error {
	if newName == "" {
		return errors.New("new name is empty")
	}
	if cfg.Client.Name == "" {
		cfg.Client = Client{Name: newName}
	} else {
		cfg.Client.Name = newName
	}
	if err := save(); err != nil {
		return fmt.Errorf("failed to persist client name: %v", err)
	}
	return nil
}

// GetClientSecretKey returns the client secret key if present.
func GetClientSecretKey() (string, bool) {
	if cfg.Client.UdpuSecretKey == "" {
		return "", false
	}
	return cfg.Client.UdpuSecretKey, true
}

// SetClientSecretKey sets the client secret key and persists it.
func SetClientSecretKey(k string) error {
	cfg.Client.UdpuSecretKey = k
	return save()
}

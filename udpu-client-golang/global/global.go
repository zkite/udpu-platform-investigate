package global

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os/exec"
	"path"
	"strconv"
	"strings"
	"time"

	"udpuClient/constants"
	"udpuClient/database"
	"udpuClient/logx"
	"udpuClient/types"

	"github.com/gorilla/websocket"
	"github.com/robfig/cron/v3"
)

var globalHTTPClient = &http.Client{Timeout: 10 * time.Second}

// WSConn is a global WebSocket connection shared across modules.
var WSConn *websocket.Conn

// Global pointers to runtime configuration.
var (
	ServerHost   *string = new(string)
	ServerPort   *int    = new(int)
	RepoHost     *string = new(string)
	RepoPort     *int    = new(int)
	SoftwarePath *string = new(string)
	MacInterface *string = new(string)
)

// JobData describes a job received from the server.
type JobData struct {
	Command          string `json:"command"`
	VbuserID         string `json:"vbuser_id"`
	Frequency        string `json:"frequency"`
	Locked           string `json:"locked"`
	RequiredSoftware string `json:"required_software"`
	Name             string `json:"name"`
	RequireOutput    string `json:"require_output"`
	JobType          string `json:"type"`
}

// QueueData describes a queue with a list of jobs.
type QueueData struct {
	Name   string `json:"name"`
	Jobs   string `json:"jobs"`
	Locked string `json:"locked"`
}

// ExecuteJobData is a minimal payload to schedule and run a job.
type ExecuteJobData struct {
	Name          string
	Command       string
	RequireOutput string
}

func sendJobLog(name, command, stdOut, stdErr string, statusCode int) {

	client, err := database.GetClient()
	if err != nil {
		logx.Fatalf("Cannot get client object")
		return
	}

	data := types.JobLog{
		Client:     client.Name,
		Name:       name,
		Command:    command,
		StdErr:     stdErr,
		StdOut:     stdOut,
		StatusCode: strconv.Itoa(statusCode),
		Timestamp:  time.Now().UTC().Format(time.RFC3339),
	}

	parts := make([]string, 0, 4)
	parts = append(parts, "api", constants.APIVersion)
	parts = append(parts, "logs", "jobs")

	p := "/" + path.Join(parts...)

	u := url.URL{
		Scheme: "http",
		Host:   net.JoinHostPort(*ServerHost, strconv.Itoa(*ServerPort)),
		Path:   p,
	}
	urlStr := u.String()

	jsonData, err := json.Marshal(data)
	if err != nil {
		logx.Fatalf("failed to marshal logs/jobs payload: %v", err)
		return
	}

	req, err := http.NewRequest("POST", urlStr, bytes.NewBuffer(jsonData))
	if err != nil {
		logx.Fatalf("failed to create logs/jobs request: %v", err)
		return
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := globalHTTPClient.Do(req)
	if err != nil {
		logx.Fatalf("failed to send logs/jobs: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logx.Infof("Received non-200 response for logs/jobs: %s", resp.Status)
	}
}

// ExecuteCommand runs a shell command and returns stdout or stderr on error.
func ExecuteCommand(command string, name string) (string, error) {
	// Normalize quotes for shell execution.
	command = strings.ReplaceAll(command, "'", "\"")
	logx.Infof("Execute command: %s", command)

	// Use /bin/sh -c to run the command string.
	cmd := exec.Command("/bin/sh", "-c", command)

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()

	output := strings.TrimSpace(stdout.String())
	errorOutput := strings.TrimSpace(stderr.String())

	exitCode := -1
	if cmd.ProcessState != nil {
		exitCode = cmd.ProcessState.ExitCode()
	}

	go sendJobLog(name, command, output, errorOutput, exitCode)

	if err != nil {
		return errorOutput, fmt.Errorf("Error: %v, stderr: %s", err, errorOutput)
	}

	return output, nil
}

// ExecuteJob runs the job once and posts result via WebSocket.
func ExecuteJob(data ExecuteJobData) {
	logx.Infof("Executing job: %+v", data)

	output, err := ExecuteCommand(data.Command, data.Name)
	if err != nil {
		logx.Infof("Error executing command: %s\nOutput: %s", err, output)
	}

	payload := map[string]string{
		"response": output,
	}

	msg, err := json.Marshal(payload)
	if err != nil {
		logx.Infof("Error marshalling payload: %v", err)
		return
	}

	if err := WSConn.WriteMessage(websocket.TextMessage, msg); err != nil {
		logx.Infof("Error sending payload: %v", err)
		return
	}

	logx.Infof("Command output %s", output)
}

// GetDataFromServer performs a GET and decodes JSON into interface{}.
func GetDataFromServer(url string) interface{} {
	resp, err := http.Get(url)
	if err != nil {
		logx.Infof("Server request error: %v", err)
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logx.Infof("Wrong response status: %d", resp.StatusCode)
		return nil
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logx.Infof("Reading response error: %v", err)
		return nil
	}

	var result interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		logx.Infof("JSON serialization error: %v", err)
		return nil
	}

	return result
}

// ConvertJobDataToMap converts JobData to a generic map for storage.
func ConvertJobDataToMap(data JobData) map[string]interface{} {
	return map[string]interface{}{
		"name":              data.Name,
		"command":           data.Command,
		"frequency":         data.Frequency,
		"locked":            data.Locked,
		"require_output":    data.RequireOutput,
		"vbuser_id":         data.VbuserID,
		"required_software": data.RequiredSoftware,
		"job_type":          data.JobType,
	}
}

// GetJobs fetches jobs for the first boot.
func GetJobs(url string) []JobData {
	var jobs []JobData

	resp, err := http.Get(url)
	if err != nil {
		logx.Infof("Error making request: %v", err)
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logx.Infof("Bad status code: %d", resp.StatusCode)
		return nil
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logx.Infof("Error reading response body: %v", err)
		return nil
	}

	if err := json.Unmarshal(body, &jobs); err != nil {
		logx.Infof("Error unmarshalling JSON: %v", err)
		return nil
	}

	return jobs
}

// ScheduleJob schedules periodic execution according to frequency.
func ScheduleJob(jobFrequency string, data ExecuteJobData) {
	c := cron.New()

	// Map frequency code to cron spec.
	var interval string
	switch jobFrequency {
	case "1":
		interval = "@every 1m"
	case "15":
		interval = "@every 15m"
	case "60":
		interval = "@every 1h"
	case "1440":
		interval = "@every 24h"
	default:
		// Unsupported frequency, do not schedule.
		return
	}

	_, err := c.AddFunc(interval, func() {
		ExecuteJob(data)
	})
	if err != nil {
		logx.Infof("Failed to schedule job: %v", err)
		return
	}

	c.Start()
}

// GetFilteredJobs requests jobs filtered by a comma-separated list.
func GetFilteredJobs(baseURL string, jobList string) ([]JobData, error) {
	u, err := url.Parse(baseURL)
	if err != nil {
		logx.Fatalf("%v", err)
		return nil, err
	}

	q := u.Query()
	q.Set("filter_by", jobList)
	u.RawQuery = q.Encode()

	resp, err := http.Get(u.String())
	if err != nil {
		logx.Fatalf("%v", err)
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		logx.Infof("Can't get filtered jobs; response status: %d", resp.StatusCode)
		return nil, fmt.Errorf("bad status: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logx.Fatalf("%v", err)
		return nil, err
	}

	var jobs []JobData
	if err := json.Unmarshal(body, &jobs); err != nil {
		logx.Fatalf("%v", err)
		return nil, err
	}

	return jobs, nil
}

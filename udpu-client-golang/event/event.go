package event

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"

	"udpuClient/constants"
	"udpuClient/database"
	"udpuClient/global"
	"udpuClient/logx"
	"udpuClient/repo"

	"github.com/gorilla/websocket"
)

// updateVbuser sends a PATCH request to update vbuser fields.
func updateVbuser(url string, payload map[string]string) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("PATCH", url, bytes.NewBuffer(data))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

// processJob executes a job and optionally updates vbuser fields.
func processJob(data global.JobData) (string, error) {
	host := fmt.Sprintf("%s:%d", *global.ServerHost, *global.ServerPort)

	if data.VbuserID != "" {
		logx.Infof("Vbuser id: %s", data.VbuserID)
		logx.Infof("Job type: %s; command: %s", data.JobType, data.Command)

		output, err := global.ExecuteCommand(data.Command, data.Name)
		if err != nil {
			logx.Infof("Error executing command: %v;", err)
			return "", err
		}

		vbuserURL := "http://" + host + "/api/v1.0/vbuser/" + data.VbuserID
		payload := map[string]string{}

		switch data.JobType {
		case "update_ep":
			payload["ghn_ep_mac"] = output
		case "update_dm":
			payload["ghn_dm_mac"] = output
		case "update_min_rate":
			payload["lq_min_rate"] = output
		case "update_max_rate":
			payload["lq_max_rate"] = output
			payload["lq_current_rate"] = output
		}

		if len(payload) > 0 {
			if err := updateVbuser(vbuserURL, payload); err != nil {
				logx.Infof("Error updating vbuser: %v", err)
			}
		}

		return output, nil
	}

	// No vbuser context. Just run the job.
	logx.Infof("Job name: %s; command: %s", data.Name, data.Command)
	output, err := global.ExecuteCommand(data.Command, data.Name)
	if err != nil {
		logx.Infof("Error executing command: %v;", err)
		return "", err
	}
	logx.Infof("Job: %s; output: %s;", data.Name, output)

	return output, nil
}

// downloadRequiredSoftware resolves software URLs and starts concurrent download.
func downloadRequiredSoftware(softwareIDs []string) {
	var requiredSoftware []string
	host := fmt.Sprintf("%s:%d", *global.RepoHost, *global.RepoPort)

	for _, softwareID := range softwareIDs {
		u := url.URL{
			Scheme: "http",
			Host:   host,
			Path:   "/api/v1.0/repo/" + softwareID,
		}

		data := global.GetDataFromServer(u.String())
		dataMap, ok := data.(map[string]interface{})
		if !ok {
			logx.Infof("JSON-object is expected")
			continue
		}

		urlStr, ok := dataMap["url"].(string)
		if !ok {
			logx.Infof("Url doesn't exist for softwareID: %s", softwareID)
			continue
		}
		requiredSoftware = append(requiredSoftware, urlStr)
	}

	if len(requiredSoftware) > 0 {
		go repo.DownloadSoftwareConcurrently(requiredSoftware, *global.SoftwarePath)
	}
}

// JobEvent handles job events: persist, schedule, execute, and optionally respond.
func JobEvent(data global.JobData) {
	// Skip locked jobs.
	if data.Locked != "false" {
		return
	}

	// Ensure required software is available.
	if data.RequiredSoftware != "None" {
		softwareIDs := strings.Split(data.RequiredSoftware, ",")
		downloadRequiredSoftware(softwareIDs)
	}

	// Upsert job in local database.
	dataMap := global.ConvertJobDataToMap(data)
	jobs := database.GetData("job", data.Name)
	if jobs == nil {
		database.CreateData("job", dataMap)
	} else {
		database.UpdateData("job", data.Name, dataMap)
	}

	// Duplicate persistence for EveryBoot per original logic.
	if data.Frequency == constants.EveryBoot && data.Command != "" {
		jobs := database.GetData("job", data.Name)
		if jobs == nil {
			database.CreateData("job", dataMap)
		} else {
			database.UpdateData("job", data.Name, dataMap)
		}
	}

	// Schedule the job according to frequency.
	executeData := global.ExecuteJobData{
		Name:          data.Name,
		Command:       data.Command,
		RequireOutput: data.RequireOutput,
	}
	global.ScheduleJob(data.Frequency, executeData)

	// Execute now and handle output.
	output, err := processJob(data)
	if err != nil {
		logx.Infof("Job failed: %v", err)
		return
	}
	logx.Infof("Command output: %s", output)

	// If output is not required, stop here.
	if data.RequireOutput == "false" {
		return
	}

	// Send output back via WebSocket.
	responseMessage := map[string]interface{}{
		"response": output,
	}
	responseMsg, err := json.Marshal(responseMessage)
	if err != nil {
		logx.Infof("Error marshalling response message: %v", err)
		return
	}

	if err = global.WSConn.WriteMessage(websocket.TextMessage, responseMsg); err != nil {
		logx.Infof("Error sending response message: %v", err)
	}
}

// QueueEvent resolves and executes jobs from a queue and optionally replies.
func QueueEvent(data global.QueueData) {
	// Skip locked queues.
	if data.Locked != "false" {
		return
	}

	serverHost := fmt.Sprintf("%s:%d", *global.ServerHost, *global.ServerPort)
	sUrl := url.URL{
		Scheme: "http",
		Host:   serverHost,
		Path:   "/api/v1.0/jobs/",
	}

	// Fetch filtered jobs for this queue.
	jobs, err := global.GetFilteredJobs(sUrl.String(), data.Jobs)
	if err != nil {
		logx.Infof("%v", err)
		return
	}

	for _, job := range jobs {
		// Ensure software presence.
		if job.RequiredSoftware != "" {
			softwareIDs := strings.Split(job.RequiredSoftware, ",")
			downloadRequiredSoftware(softwareIDs)
		}

		// Execute only if output is required.
		if job.RequireOutput == "true" {
			output, err := global.ExecuteCommand(job.Command, job.Name)
			if err != nil {
				logx.Infof("Error executing command: %v;", err)
				continue
			}

			responseMessage := map[string]interface{}{
				"response": output,
			}
			responseMsg, err := json.Marshal(responseMessage)
			if err != nil {
				logx.Infof("Error marshalling response message: %v", err)
				continue
			}

			if err = global.WSConn.WriteMessage(websocket.TextMessage, responseMsg); err != nil {
				logx.Infof("Error sending response message: %v", err)
			}
		}
	}
}

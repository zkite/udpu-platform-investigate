package process

import (
	"encoding/json"

	"udpuClient/constants"
	"udpuClient/database"
	"udpuClient/event"
	"udpuClient/global"
	"udpuClient/jobs"
	"udpuClient/logx"
	"udpuClient/response"
	"udpuClient/rest"
	"udpuClient/types"
)

// ProcessAndRespondAsync handles incoming WS messages asynchronously.
func ProcessAndRespondAsync(message []byte) {
	go func() {
		// Extract action_type to route the message.
		var requestMessage struct {
			ActionType string `json:"action_type"`
		}
		if err := json.Unmarshal(message, &requestMessage); err != nil {
			logx.Infof("Error unmarshalling message to get action_type: %v", err)
			return
		}

		switch requestMessage.ActionType {
		case "job":
			// Decode and process a job event.
			var jobData global.JobData
			if err := json.Unmarshal(message, &jobData); err != nil {
				logx.Infof("Error unmarshalling job message: %v", err)
				return
			}
			event.JobEvent(jobData)

		case "queue":
			// Decode and process a queue event.
			var queueData global.QueueData
			if err := json.Unmarshal(message, &queueData); err != nil {
				logx.Infof("Error unmarshalling queue message: %v", err)
				return
			}
			event.QueueEvent(queueData)

		default:
			logx.Infof("Unknown action type: %s", requestMessage.ActionType)
		}
	}()
}

// ProcessUdpuData persists client data and starts job processing flows.
func ProcessUdpuData(respObj *response.ServerResponse) {
	data := database.GetData("client", respObj.SubscriberUID)
	if data == nil {
		if err := database.InsertIntoClient(respObj); err != nil {
			logx.Fatalf("Failed to insert data into client table: %v", err)
		}
	} else {
		fields := types.NewUdpuUpdate(respObj).ToMap()
		database.UpdateData("client", respObj.SubscriberUID, fields)
	}

	client, err := database.GetClient()
	if err != nil {
		logx.Fatalf("Cannot get client object")
		return
	}

	if client.BootStatus == constants.BootStatusFirst {
		urlStr := rest.CreateURL("http", nil, "roles", client.UdpuRole, "jobs")
		firstBootJobsList := global.GetJobs(urlStr)

		if firstBootJobsList != nil {
			jobs.UpdateJobs(firstBootJobsList)
			jobs.ProcessJobs(database.GetFirstBootJobs())
		}
	}

	if client.BootStatus == constants.BootStatusRegular {
		urlStr := rest.CreateURL("http", nil, "jobs", "frequency", "every_boot")
		everyBootJobsList := global.GetJobs(urlStr)

		if everyBootJobsList != nil {
			jobs.UpdateJobs(everyBootJobsList)
		}

		jobs.ProcessJobs(database.GetEveryBootJobs())
	}

	jobs.ProcessScheduledJobs(database.GetJobsScheduled())
}

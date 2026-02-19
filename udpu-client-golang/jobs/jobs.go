package jobs

import (
	"udpuClient/database"
	"udpuClient/global"
	"udpuClient/logx"
)

// executeJobFromMap validates the map and executes the job.
func executeJobFromMap(jobData map[string]interface{}) {
	name, ok := jobData["name"].(string)
	if !ok {
		logx.Infof("Invalid job name")
		return
	}
	command, ok := jobData["command"].(string)
	if !ok {
		logx.Infof("Invalid job command")
		return
	}
	requireOutput, ok := jobData["require_output"].(string)
	if !ok {
		logx.Infof("Invalid require_output value")
		return
	}
	job := global.ExecuteJobData{
		Name:          name,
		Command:       command,
		RequireOutput: requireOutput,
	}
	global.ExecuteJob(job)
}

// ProcessJobs starts execution for unlocked jobs.
func ProcessJobs(jobs []map[string]interface{}) {
	for _, jobData := range jobs {
		if locked, ok := jobData["locked"].(string); !ok || locked != "true" {
			go executeJobFromMap(jobData)
		}
	}
}

// UpdateJobs upserts jobs into the local database.
func UpdateJobs(jobList []global.JobData) {
	for _, job := range jobList {
		jobData := global.ConvertJobDataToMap(job)
		if data := database.GetData("job", job.Name); data == nil {
			database.CreateData("job", jobData)
		} else {
			database.UpdateData("job", job.Name, jobData)
		}
	}
}

// ProcessScheduledJobs schedules periodic execution for jobs.
func ProcessScheduledJobs(jobs []map[string]interface{}) {
	for _, jobData := range jobs {
		name, ok1 := jobData["name"].(string)
		command, ok2 := jobData["command"].(string)
		requireOutput, ok3 := jobData["require_output"].(string)
		frequency, ok4 := jobData["frequency"].(string)
		if !ok1 || !ok2 || !ok3 || !ok4 {
			logx.Infof("Invalid scheduled job data")
			continue
		}
		executeData := global.ExecuteJobData{
			Name:          name,
			Command:       command,
			RequireOutput: requireOutput,
		}
		global.ScheduleJob(frequency, executeData)
	}
}

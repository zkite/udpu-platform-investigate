package repo

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"udpuClient/logx"
)

// getFileNameFromURL derives a filename from URL or returns a timestamped default.
func getFileNameFromURL(url string) string {
	defaultFileName := fmt.Sprintf("default_name_%v", time.Now().Unix())
	if url == "" {
		return defaultFileName
	}
	splits := strings.Split(url, "/")
	if len(splits) == 0 {
		return defaultFileName
	}
	fileName := splits[len(splits)-1]
	if fileName == "" {
		return defaultFileName
	}
	return fileName
}

// downloadFile fetches a single file and writes it to filePath dir.
// Returns success flag and the final filename.
func downloadFile(url, filePath string) (bool, string) {
	if url == "" {
		return false, ""
	}
	resp, err := http.Get(url)
	if err != nil {
		return false, ""
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK {
		fileName := getFileNameFromURL(url)
		filePath = filepath.Join(filePath, fileName)

		file, err := os.Create(filePath)
		if err != nil {
			return false, ""
		}
		defer file.Close()

		if _, err = io.Copy(file, resp.Body); err != nil {
			return false, ""
		}
		return true, fileName
	}
	return false, ""
}

// DownloadSoftwareConcurrently downloads a list of files in parallel.
func DownloadSoftwareConcurrently(softwareList []string, softwarePath string) {
	var wg sync.WaitGroup
	wg.Add(len(softwareList))

	for _, url := range softwareList {
		go func(url string) {
			defer wg.Done()
			isDownloaded, fileName := downloadFile(url, softwarePath)
			logx.Infof("Download file: %s, status: %v", fileName, isDownloaded)
		}(url)
	}

	wg.Wait()
}

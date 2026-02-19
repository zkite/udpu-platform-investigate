package ws

import (
	"net/url"
	"time"

	"udpuClient/global"
	"udpuClient/logx"
	"udpuClient/process"
	"udpuClient/rest"

	"github.com/gorilla/websocket"
)

// connectWS dials WS endpoint with channel=subscriberUID.
func connectWS(subscriberUID string) (*websocket.Conn, error) {
	params := url.Values{}
	params.Set("channel", subscriberUID)

	wsURL := rest.CreateURL("ws", params, "pubsub")
	c, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		return nil, err
	}
	return c, nil
}

// InitWS connects with retry loop and stores connection globally.
func InitWS(subscriberUID string) *websocket.Conn {
	for {
		conn, err := connectWS(subscriberUID)
		if err != nil {
			logx.Infof("WebSocket connection error: %v. Retrying in 5 seconds...", err)
			time.Sleep(5 * time.Second)
			continue
		}
		logx.Infof("WebSocket connected successfully")
		global.WSConn = conn
		return conn
	}
}

// ListenWS reads messages forever and dispatches processing.
func ListenWS() error {
	for {
		_, message, err := global.WSConn.ReadMessage()
		if err != nil {
			logx.Infof("WebSocket read error: %v", err)
			return err
		}
		process.ProcessAndRespondAsync(message)
	}
}

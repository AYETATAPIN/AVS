package mqtt

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"device-go/internal/config"
	"device-go/internal/models"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

type Client struct {
    client  mqtt.Client
    handler *Handler
    cfg     *config.Config
}

func NewClient(cfg *config.Config, waiter *ResponseWaiter) *Client {
    return &Client{
        cfg:     cfg,
        handler: NewHandler(waiter),
    }
}

func (c *Client) Connect() error {
    opts := mqtt.NewClientOptions()
    opts.AddBroker(c.cfg.MQTTBroker)
    opts.SetClientID("device-go-" + time.Now().Format("20060102150405"))
    opts.SetCleanSession(true)
    opts.SetAutoReconnect(true)
    opts.SetMaxReconnectInterval(10 * time.Second)
    if c.cfg.MQTTUsername != "" {
        opts.SetUsername(c.cfg.MQTTUsername)
        opts.SetPassword(c.cfg.MQTTPassword)
    }

    opts.OnConnect = func(cl mqtt.Client) {
        log.Println("Connected to MQTT broker")
        // Подписываемся на топик ответов
        if token := cl.Subscribe("devices/+/response", 1, c.handler.HandleMessage); token.Wait() && token.Error() != nil {
            log.Printf("Failed to subscribe to devices/+/response: %v", token.Error())
        } else {
            log.Println("Subscribed to devices/+/response")
        }
    }

    opts.OnConnectionLost = func(cl mqtt.Client, err error) {
        log.Printf("MQTT connection lost: %v", err)
    }

    c.client = mqtt.NewClient(opts)
    if token := c.client.Connect(); token.Wait() && token.Error() != nil {
        return token.Error()
    }
    return nil
}

func (c *Client) Disconnect() {
    if c.client != nil && c.client.IsConnected() {
        c.client.Disconnect(250)
    }
}

// PublishCommand публикует команду в топик устройства
func (c *Client) PublishCommand(deviceID string, cmd *models.MQTTCommand) error {
    topic := fmt.Sprintf("devices/%s/commands", deviceID)
    payload, err := json.Marshal(cmd)
    if err != nil {
        return err
    }
    
    log.Printf("Publishing command to %s: command_id=%s, command=%s, parameters=%v",
        topic, cmd.CommandID, cmd.Command, cmd.Parameters)
    
    token := c.client.Publish(topic, 1, false, payload)
    token.Wait()
    if token.Error() != nil {
        log.Printf("Failed to publish command %s: %v", cmd.CommandID, token.Error())
        return token.Error()
    }
    
    log.Printf("Successfully published command %s", cmd.CommandID)
    return nil
}

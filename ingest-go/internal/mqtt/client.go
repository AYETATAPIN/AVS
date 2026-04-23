package mqtt

import (
    "log"
    "time"

    mqtt "github.com/eclipse/paho.mqtt.golang"
)

type Client struct {
    client mqtt.Client
    handler *Handler
}

func NewClient(opts *mqtt.ClientOptions, handler *Handler) *Client {
    return &Client{
        client:  mqtt.NewClient(opts),
        handler: handler,
    }
}

func NewClientOptions(broker, clientID string) *mqtt.ClientOptions {
    opts := mqtt.NewClientOptions()
    opts.AddBroker(broker)
    opts.SetClientID(clientID + "-" + time.Now().Format("20060102150405"))
    opts.SetCleanSession(true)
    opts.SetConnectTimeout(30 * time.Second)
    opts.SetAutoReconnect(true)
    opts.SetMaxReconnectInterval(10 * time.Second)
    
    // Callback-и
    opts.OnConnect = func(c mqtt.Client) {
        log.Println("Connected to MQTT broker")
    }
    
    opts.OnConnectionLost = func(c mqtt.Client, err error) {
        log.Printf("MQTT connection lost: %v", err)
    }
    
    opts.OnReconnecting = func(c mqtt.Client, co *mqtt.ClientOptions) {
        log.Println("Reconnecting to MQTT broker...")
    }
    
    return opts
}

func (c *Client) Connect() error {
    if token := c.client.Connect(); token.Wait() && token.Error() != nil {
        return token.Error()
    }
    return nil
}

func (c *Client) Disconnect() {
    c.client.Disconnect(250)
}

func (c *Client) Subscribe(topic string, qos byte) error {
    token := c.client.Subscribe(topic, qos, c.handler.HandleMessage)
    if token.Wait() && token.Error() != nil {
        return token.Error()
    }
    return nil
}
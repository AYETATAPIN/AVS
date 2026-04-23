package mqtt

import (
    "encoding/json"
    "log"

    mqtt "github.com/eclipse/paho.mqtt.golang"
    "device-go/internal/models"
)

type Handler struct {
    waiter *ResponseWaiter
}

func NewHandler(waiter *ResponseWaiter) *Handler {
    return &Handler{
        waiter: waiter,
    }
}

func (h *Handler) HandleMessage(client mqtt.Client, msg mqtt.Message) {
    log.Printf("Received response on topic %s: %s", msg.Topic(), string(msg.Payload()))

    var resp models.MQTTResponse
    if err := json.Unmarshal(msg.Payload(), &resp); err != nil {
        log.Printf("Failed to parse response JSON: %v", err)
        return
    }

    // Доставляем ответ ожидающему HTTP-запросу
    h.waiter.Deliver(&resp)
}
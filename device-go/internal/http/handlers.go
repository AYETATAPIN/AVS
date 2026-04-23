package http

import (
    "encoding/json"
    "net/http"
    "slices"
    "time"

    "github.com/google/uuid"
    "device-go/internal/mqtt"
    "device-go/internal/models"
)

type Handlers struct {
    mqttClient *mqtt.Client
    waiter     *mqtt.ResponseWaiter
    timeout    time.Duration
}

func NewHandlers(mqttClient *mqtt.Client, waiter *mqtt.ResponseWaiter, timeoutSec int) *Handlers {
    return &Handlers{
        mqttClient: mqttClient,
        waiter:     waiter,
        timeout:    time.Duration(timeoutSec) * time.Second,
    }
}

// SendCommand обрабатывает POST /api/commands
func (h *Handlers) SendCommand(w http.ResponseWriter, r *http.Request) {
    var req models.CommandRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid request body", http.StatusBadRequest)
        return
    }
    if req.DeviceID == "" || req.Command == "" {
        http.Error(w, "device_id and command are required", http.StatusBadRequest)
        return
    }

    if !slices.Contains(models.AllCommands(), req.Command) {
        http.Error(w, "unsupported command", http.StatusBadRequest)
        return
    }

    cmdID := uuid.New().String()
    mqttCmd := &models.MQTTCommand{
        CommandID:  cmdID,
        Command:    req.Command,
        Parameters: req.Parameters,
    }

    // Регистрируем ожидание ответа
    respChan := h.waiter.Register(cmdID)
    defer h.waiter.Unregister(cmdID)

    // Публикуем команду
    if err := h.mqttClient.PublishCommand(req.DeviceID, mqttCmd); err != nil {
        http.Error(w, "Failed to publish command to MQTT", http.StatusInternalServerError)
        return
    }

    // Ожидаем ответ или таймаут
    select {
    case resp := <-respChan:
        // Успешный ответ от устройства
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(resp)
    case <-time.After(h.timeout):
        http.Error(w, "Timeout waiting for device response", http.StatusGatewayTimeout)
    }
}

// ListCommands остаётся без изменений
func (h *Handlers) ListCommands(w http.ResponseWriter, r *http.Request) {
    commands := models.AllCommands()
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(commands)
}
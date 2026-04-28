package http

import (
	"encoding/json"
	"fmt"
	"net/http"
	"slices"
	"time"

	"device-go/internal/models"
	"device-go/internal/mqtt"

	"github.com/google/uuid"
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

	// Формируем MQTT топик
	var topic string
	if req.DeviceID == "broadcast" {
		topic = "devices/register/broadcast"
    } else if req.DeviceID == "dynamic" && req.Command == "register" {
        buildingRussian, ok1 := req.Parameters["building_name"].(string)
        roomRussian, ok2 := req.Parameters["room_number"].(string)
        if !ok1 || !ok2 || buildingRussian == "" || roomRussian == "" {
            http.Error(w, "missing building_name or room_number for dynamic register", http.StatusBadRequest)
            return
        }
        // Преобразуем русские названия в английские для ESP32
        buildingEnglish := models.ConvertBuildingToEnglish(buildingRussian)
        roomEnglish := models.ConvertRoomNumberToEnglish(roomRussian)
        topic = fmt.Sprintf("devices/register/%s/%s", buildingEnglish, roomEnglish)
        // Также обновляем параметры команды, чтобы устройство получило английские значения
        mqttCmd.Parameters["building_name"] = buildingEnglish
        mqttCmd.Parameters["room_number"] = roomEnglish
	} else {
		topic = fmt.Sprintf("devices/%s/commands", req.DeviceID)
	}

	// Регистрируем ожидание ответа
	respChan := h.waiter.Register(cmdID)
	defer h.waiter.Unregister(cmdID)

	// Публикуем команду
	if err := h.mqttClient.PublishCommandToTopic(topic, mqttCmd); err != nil {
		http.Error(w, "Failed to publish command to MQTT", http.StatusInternalServerError)
		return
	}

	// Ожидаем ответ или таймаут
	select {
	case resp := <-respChan:
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

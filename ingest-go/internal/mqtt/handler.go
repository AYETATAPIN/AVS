package mqtt

import (
    "encoding/json"
    "log"
    "strings"
    "time"

    mqtt "github.com/eclipse/paho.mqtt.golang"
    "ingest-go/internal/models"
    "ingest-go/internal/storage"
)

type Handler struct {
    db    *storage.PostgresDB
    redis *storage.RedisClient
}

func NewHandler(db *storage.PostgresDB, redis *storage.RedisClient) *Handler {
    return &Handler{db: db, redis: redis}
}

func (h *Handler) HandleMessage(client mqtt.Client, msg mqtt.Message) {
    topic := msg.Topic()
    log.Printf("MQTT message on %s", topic)

    switch {
    case strings.HasPrefix(topic, "sensors/") && strings.HasSuffix(topic, "/data"):
        h.handleSensorData(msg.Payload())
    case strings.HasPrefix(topic, "sensors/") && strings.HasSuffix(topic, "/status"):
        h.handleSensorStatus(msg.Payload())
    case strings.HasPrefix(topic, "commands/"):
        h.handleCommand(msg.Payload())
    }
}

func (h *Handler) handleSensorData(payload []byte) {
    var mqttMsg models.MQTTMessage
    if err := json.Unmarshal(payload, &mqttMsg); err != nil {
        log.Printf("JSON parse error: %v", err)
        return
    }

    data := models.SensorData{
        SensorID:     mqttMsg.SensorID,
        BuildingName: models.GetRussianBuildingName(mqttMsg.BuildingName),
        RoomNumber:   models.ConvertRoomNumber(mqttMsg.RoomNumber),
        TS:           mqttMsg.TS,
        CO2:          mqttMsg.CO2,
        Temperature:  mqttMsg.Temperature,
        Humidity:     mqttMsg.Humidity,
    }
    if data.TS.IsZero() {
        data.TS = time.Now()
    }

    if err := h.db.CreateSensorData(&data); err != nil {
        log.Printf("DB save error: %v", err)
        return
    }

    if h.redis != nil {
        if b, err := json.Marshal(data); err == nil {
            h.redis.SetDeviceData(data.SensorID, b, 24*time.Hour)
        }
    }

    log.Printf("Saved: %s (%s, %s) CO2=%d Temp=%d Hum=%d",
        data.SensorID, data.BuildingName, data.RoomNumber,
        data.CO2, data.Temperature, data.Humidity)
}

func (h *Handler) handleSensorStatus(payload []byte) {
    log.Printf("Status: %s", payload)
}

func (h *Handler) handleCommand(payload []byte) {
    log.Printf("Command: %s", payload)
}
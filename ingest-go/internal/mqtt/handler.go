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

// redisRecord — формат, который ожидает api-java при чтении HGETALL avs:sensors:current.
// Поля идут в camelCase, потому что Jackson на стороне Java маппит их в RecordEntity.
type redisRecord struct {
    ID           uint      `json:"id"`
    SensorID     string    `json:"sensorId"`
    BuildingName string    `json:"buildingName"`
    RoomNumber   string    `json:"roomNumber"`
    TS           time.Time `json:"ts"`
    CO2          int       `json:"co2"`
    Temperature  int       `json:"temperature"`
    Humidity     int       `json:"humidity"`
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
        log.Printf("Error parsing sensor data JSON: %v", err)
        log.Printf("Raw payload: %s", string(payload))
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
        log.Printf("Error saving sensor data to PostgreSQL: %v", err)
        return
    }

    if h.redis != nil {
        rec := redisRecord{
            ID:           data.ID,
            SensorID:     data.SensorID,
            BuildingName: data.BuildingName,
            RoomNumber:   data.RoomNumber,
            TS:           data.TS,
            CO2:          data.CO2,
            Temperature:  data.Temperature,
            Humidity:     data.Humidity,
        }
        if b, err := json.Marshal(rec); err != nil {
            log.Printf("Error marshaling Redis current record: %v", err)
        } else if err := h.redis.SetCurrentSensorRecord(data.SensorID, b); err != nil {
            log.Printf("Error writing Redis current record: %v", err)
        }
    }

    log.Printf("MQTT: %s/%s (english) -> DB: %s/%s (russian)",
        mqttMsg.BuildingName, mqttMsg.RoomNumber,
        data.BuildingName, data.RoomNumber)
    log.Printf("Saved: %s (%s, %s) - CO2: %dppm, Temp: %d°C, Humidity: %d%%",
        data.SensorID, data.BuildingName, data.RoomNumber,
        data.CO2, data.Temperature, data.Humidity)
}

func (h *Handler) handleSensorStatus(payload []byte) {
    log.Printf("Sensor status: %s", string(payload))
}

func (h *Handler) handleCommand(payload []byte) {
    log.Printf("Command received: %s", string(payload))
}

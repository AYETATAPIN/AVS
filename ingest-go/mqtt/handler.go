package mqtt

import (
    "encoding/json"
    "log"
    "strings"
    "time"

    mqtt "github.com/eclipse/paho.mqtt.golang"
    "ingest-go/models"
    "ingest-go/storage"
)

type Handler struct {
    db *storage.PostgresDB
}

func NewHandler(db *storage.PostgresDB) *Handler {
    return &Handler{db: db}
}

// HandleMessage - обработчик всех MQTT сообщений
func (h *Handler) HandleMessage(client mqtt.Client, msg mqtt.Message) {
    log.Printf("Received MQTT message on topic: %s", msg.Topic())
    
    // Обрабатываем в зависимости от топика
    if strings.HasPrefix(msg.Topic(), "sensors/") && strings.HasSuffix(msg.Topic(), "/data") {
        h.handleSensorData(msg.Payload())
    } else if strings.HasPrefix(msg.Topic(), "sensors/") && strings.HasSuffix(msg.Topic(), "/status") {
        h.handleSensorStatus(msg.Payload())
    } else if strings.HasPrefix(msg.Topic(), "commands/") {
        h.handleCommand(msg.Payload())
    }
}

func (h *Handler) handleSensorData(payload []byte) {
    var mqttMsg models.MQTTMessage
    if err := json.Unmarshal(payload, &mqttMsg); err != nil {
        log.Printf("Error parsing sensor data JSON: %v", err)
        return
    }
    
    // Преобразуем в модель БД
    sensorData := models.SensorData{
        SensorID:     mqttMsg.SensorID,
        BuildingName: mqttMsg.BuildingName,
        RoomNumber:   mqttMsg.RoomNumber,
        TS:           mqttMsg.TS,
        CO2:          mqttMsg.CO2,
        Temperature:  mqttMsg.Temperature,
        Humidity:     mqttMsg.Humidity,
    }
    
    // Если время не указано, используем текущее
    if sensorData.TS.IsZero() {
        sensorData.TS = time.Now()
    }
    
    // Сохраняем в PostgreSQL
    if err := h.db.CreateSensorData(&sensorData); err != nil {
        log.Printf("Error saving sensor data to PostgreSQL: %v", err)
        return
    }
    
    log.Printf("Saved: %s (%s) - CO2: %dppm, Temp: %d°C, Humidity: %d%%", 
        sensorData.SensorID, sensorData.RoomNumber,
        sensorData.CO2, sensorData.Temperature, sensorData.Humidity)
}

func (h *Handler) handleSensorStatus(payload []byte) {
    // Обработка статуса сенсора
    log.Printf("Sensor status: %s", string(payload))
}

func (h *Handler) handleCommand(payload []byte) {
    // Обработка команд (перезагрузка, обновление и т.д.)
    log.Printf("Command received: %s", string(payload))
}
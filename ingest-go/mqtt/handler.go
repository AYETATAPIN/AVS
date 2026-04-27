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
    redis *storage.RedisClient
}

func NewHandler(db *storage.PostgresDB, redis *storage.RedisClient) *Handler {
    return &Handler{db: db, redis: redis}
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
        log.Printf("Raw payload: %s", string(payload))
        return
    }
    
    // Преобразуем английское название из MQTT в русское для БД
    russianBuildingName := models.GetRussianBuildingName(mqttMsg.BuildingName)
    
    // Преобразуем номер комнаты (английские буквы -> русские)
    russianRoomNumber := models.ConvertRoomNumber(mqttMsg.RoomNumber)
    
    // Преобразуем в модель БД
    sensorData := models.SensorData{
        SensorID:     mqttMsg.SensorID,
        BuildingName: russianBuildingName, // Сохраняем русское название
        RoomNumber:   russianRoomNumber,   // Сохраняем номер с русской буквой
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

    // Обновляем "текущее состояние" в Redis (если подключен)
    if h.redis != nil {
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
        rec := redisRecord{
            ID:           sensorData.ID,
            SensorID:     sensorData.SensorID,
            BuildingName: sensorData.BuildingName,
            RoomNumber:   sensorData.RoomNumber,
            TS:           sensorData.TS,
            CO2:          sensorData.CO2,
            Temperature:  sensorData.Temperature,
            Humidity:     sensorData.Humidity,
        }
        b, err := json.Marshal(rec)
        if err != nil {
            log.Printf("Error marshaling Redis current record: %v", err)
        } else if err := h.redis.SetCurrentSensorRecord(sensorData.SensorID, b); err != nil {
            log.Printf("Error writing Redis current record: %v", err)
        }
    }
    
    log.Printf("MQTT: %s/%s (english) -> DB: %s/%s (russian)", 
        mqttMsg.BuildingName, mqttMsg.RoomNumber, 
        sensorData.BuildingName, sensorData.RoomNumber)
    log.Printf("Saved: %s (%s, %s) - CO2: %dppm, Temp: %d°C, Humidity: %d%%", 
        sensorData.SensorID, sensorData.BuildingName, sensorData.RoomNumber,
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
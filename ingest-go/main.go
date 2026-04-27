package main

import (
    "encoding/json"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"

    "ingest-go/config"
    "ingest-go/mqtt"
    "ingest-go/storage"
)

func main() {
    // Загружаем конфигурацию
    cfg := config.Load()
    
    log.Println("Starting AVS Ingest Service...")
    log.Printf("MQTT Broker: %s", cfg.MQTTBroker)
    log.Printf("PostgreSQL: %s", cfg.PostgresURL)
    
    // Инициализируем хранилище
    db, err := storage.NewPostgres(cfg.PostgresURL)
    if err != nil {
        log.Fatalf("Failed to connect to PostgreSQL: %v", err)
    }
    defer db.Close()
    
    log.Println("PostgreSQL connection established")

    // Инициализируем Redis (опционально)
    var redisClient *storage.RedisClient
    if cfg.RedisURL != "" {
        redisClient = storage.NewRedisClient(cfg.RedisURL)
        defer redisClient.Close()

        // Backfill Redis "current state" from PostgreSQL on startup
        current, err := db.GetCurrentState()
        if err != nil {
            log.Printf("Redis backfill skipped (failed to read current state from PostgreSQL): %v", err)
        } else {
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

            ok := 0
            for _, row := range current {
                rec := redisRecord{
                    ID:           row.ID,
                    SensorID:     row.SensorID,
                    BuildingName: row.BuildingName,
                    RoomNumber:   row.RoomNumber,
                    TS:           row.TS,
                    CO2:          row.CO2,
                    Temperature:  row.Temperature,
                    Humidity:     row.Humidity,
                }
                b, err := json.Marshal(rec)
                if err != nil {
                    continue
                }
                if err := redisClient.SetCurrentSensorRecord(row.SensorID, b); err != nil {
                    continue
                }
                ok++
            }
            log.Printf("Redis backfill complete: %d sensor current records", ok)
        }
    }
    
    // Инициализируем MQTT обработчик
    handler := mqtt.NewHandler(db, redisClient)
    
    // Настраиваем MQTT клиент
    mqttOpts := mqtt.NewClientOptions(cfg.MQTTBroker, "avs-ingest")
    if cfg.MQTTUsername != "" {
        mqttOpts.SetUsername(cfg.MQTTUsername)
        mqttOpts.SetPassword(cfg.MQTTPassword)
    }
    client := mqtt.NewClient(mqttOpts, handler)
    
    if err := client.Connect(); err != nil {
        log.Fatalf("Failed to connect to MQTT: %v", err)
    }
    defer client.Disconnect()
    
    log.Println("MQTT connection established")
    
    // Подписываемся на топики
    topics := []string{
        "sensors/+/data",      // Данные от сенсоров
        "sensors/+/status",    // Статус сенсоров
        "commands/+/+",        // Команды для сенсоров
    }
    
    for _, topic := range topics {
        if err := client.Subscribe(topic, 1); err != nil {
            log.Printf("Failed to subscribe to %s: %v", topic, err)
        } else {
            log.Printf("Subscribed to: %s", topic)
        }
    }
    
    // Ожидаем сигнал завершения
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
    
    log.Println("Service is running. Press Ctrl+C to stop.")
    
    // Graceful shutdown
    <-sigChan
    log.Println("Shutting down...")
    
    // Даем время на завершение операций
    time.Sleep(2 * time.Second)
    log.Println("Service stopped")
}
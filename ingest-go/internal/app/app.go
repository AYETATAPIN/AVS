package app

import (
    "encoding/json"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"

    "ingest-go/internal/config"
    "ingest-go/internal/mqtt"
    "ingest-go/internal/storage"
)

func Run(cfg *config.Config) error {
    log.Println("Starting AVS Ingest Service...")
    log.Printf("MQTT Broker: %s", cfg.MQTTBroker)
    log.Printf("PostgreSQL: %s", cfg.PostgresURL)

    // PostgreSQL
    db, err := storage.NewPostgres(cfg.PostgresURL)
    if err != nil {
        return err
    }
    defer db.Close()
    log.Println("PostgreSQL connection established")

    // Опционально Redis (если URL задан)
    var redisClient *storage.RedisClient
    if cfg.RedisURL != "" {
        redisClient = storage.NewRedisClient(cfg.RedisURL)
        defer redisClient.Close()
        log.Println("Redis connection established")

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

    // MQTT
    handler := mqtt.NewHandler(db, redisClient)
	defer handler.Close()
    mqttOpts := mqtt.NewClientOptions(cfg.MQTTBroker, "avs-ingest")
    if cfg.MQTTUsername != "" {
        mqttOpts.SetUsername(cfg.MQTTUsername)
        mqttOpts.SetPassword(cfg.MQTTPassword)
    }
    client := mqtt.NewClient(mqttOpts, handler)

    if err := client.Connect(); err != nil {
        return err
    }
    defer client.Disconnect()
    log.Println("MQTT connection established")



    // Graceful shutdown
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
    log.Println("Service is running. Press Ctrl+C to stop.")
    <-sigChan
    log.Println("Shutting down...")
    time.Sleep(2 * time.Second)
    log.Println("Service stopped")
    return nil
}
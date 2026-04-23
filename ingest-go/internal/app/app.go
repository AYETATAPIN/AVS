package app

import (
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
    }

    // MQTT
    handler := mqtt.NewHandler(db, redisClient) // можно передать redis для кэширования
    mqttOpts := mqtt.NewClientOptions(cfg.MQTTBroker, "avs-ingest")
    client := mqtt.NewClient(mqttOpts, handler)

    if err := client.Connect(); err != nil {
        return err
    }
    defer client.Disconnect()
    log.Println("MQTT connection established")

    // Подписки
    topics := []string{
        "sensors/+/data",
        "sensors/+/status",
        "commands/+/+",
    }
    for _, topic := range topics {
        if err := client.Subscribe(topic, 1); err != nil {
            log.Printf("Failed to subscribe to %s: %v", topic, err)
        } else {
            log.Printf("Subscribed to: %s", topic)
        }
    }

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
package main

import (
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
        log.Fatalf("❌ Failed to connect to PostgreSQL: %v", err)
    }
    defer db.Close()
    
    log.Println("PostgreSQL connection established")
    
    // Инициализируем MQTT обработчик
    handler := mqtt.NewHandler(db)
    
    // Настраиваем MQTT клиент
    mqttOpts := mqtt.NewClientOptions(cfg.MQTTBroker, "avs-ingest")
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
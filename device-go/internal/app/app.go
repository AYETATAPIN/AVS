package app

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "device-go/internal/config"
    devicehttp "device-go/internal/http"
    "device-go/internal/mqtt"
)

func Run(cfg *config.Config) error {
    log.Println("Starting Device Service...")
    log.Printf("HTTP Port: %d", cfg.HTTPPort)
    log.Printf("MQTT Broker: %s", cfg.MQTTBroker)
    log.Printf("Command timeout: %d seconds", cfg.CommandTimeoutSec)

    // Инициализация менеджера ожидающих ответов
    waiter := mqtt.NewResponseWaiter()

    // MQTT клиент
    mqttClient := mqtt.NewClient(cfg, waiter)
    if err := mqttClient.Connect(); err != nil {
        return err
    }
    defer mqttClient.Disconnect()

    // HTTP сервер
    httpHandlers := devicehttp.NewHandlers(mqttClient, waiter, cfg.CommandTimeoutSec)
    httpServer := devicehttp.NewServer(httpHandlers, cfg.HTTPPort)

    // Graceful shutdown
    sigChan := make(chan os.Signal, 1)
    signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

    go func() {
        if err := httpServer.Start(); err != nil && err != http.ErrServerClosed {
            log.Printf("HTTP server error: %v", err)
        }
    }()

    log.Println("Service is running. Press Ctrl+C to stop.")
    <-sigChan

    log.Println("Shutting down...")
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    if err := httpServer.Shutdown(ctx); err != nil {
        log.Printf("HTTP server shutdown error: %v", err)
    }
    log.Println("Service stopped")
    return nil
}
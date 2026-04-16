package config

import (
    "os"
    "strings"
)

type Config struct {
    // MQTT
    MQTTBroker   string
    MQTTUsername string
    MQTTPassword string
    
    // PostgreSQL
    PostgresURL string
    
    // Redis (опционально)
    RedisURL string
    
    // Логирование
    LogLevel string
}

func Load() *Config {
    return &Config{
        MQTTBroker:   getRequiredEnv("MQTT_BROKER"),
        MQTTUsername: getEnv("MQTT_USERNAME"),
        MQTTPassword: getEnv("MQTT_PASSWORD"),
        PostgresURL:  getRequiredEnv("POSTGRES_URL"),
        RedisURL:     getEnv("REDIS_URL"),
        LogLevel:     getRequiredEnv("LOG_LEVEL"),
    }
}

func getEnv(key string) string {
    value := os.Getenv(key)
    return strings.TrimSpace(value)
}

func getRequiredEnv(key string) string {
    value := os.Getenv(key)
    if strings.TrimSpace(value) == "" {
        panic("required environment variable is not set: " + key)
    }
    return value
}
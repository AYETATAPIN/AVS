package config

import (
    "os"
    "strings"

    "github.com/joho/godotenv"
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
    // Пробуем загрузить .env файл
    _ = godotenv.Load()
    
    return &Config{
        MQTTBroker:   getEnv("MQTT_BROKER", "tcp://localhost:1883"),
        MQTTUsername: getEnv("MQTT_USERNAME", ""),
        MQTTPassword: getEnv("MQTT_PASSWORD", ""),
        PostgresURL:  getEnv("POSTGRES_URL", "postgres://avs:avs_pass@localhost:5432/avsdb?sslmode=disable"),
        RedisURL:     getEnv("REDIS_URL", ""),
        LogLevel:     getEnv("LOG_LEVEL", "info"),
    }
}

func getEnv(key, defaultValue string) string {
    value := os.Getenv(key)
    if strings.TrimSpace(value) == "" {
        return defaultValue
    }
    return value
}
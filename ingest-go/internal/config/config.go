package config

import (
	"os"
	"strconv"
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

func getEnvAsInt(key string, def int) int {
    v := getEnv(key)
    if v == "" {
        return def
    }
    i, err := strconv.Atoi(v)
    if err != nil {
        return def
    }
    return i
}
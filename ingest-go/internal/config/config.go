package config

import (
    "os"
    "strings"
)

type Config struct {
    MQTTBroker   string
    MQTTUsername string
    MQTTPassword string

    PostgresURL string

    RedisURL string

    LogLevel string
}

func Load() *Config {
    mqttUser := getEnv("MQTT_USERNAME")
    if mqttUser == "" {
        mqttUser = getEnv("MQTT_USER")
    }
    mqttPass := getEnv("MQTT_PASSWORD")
    if mqttPass == "" {
        mqttPass = getEnv("MQTT_PASS")
    }

    return &Config{
        MQTTBroker:   getRequiredEnv("MQTT_BROKER"),
        MQTTUsername: mqttUser,
        MQTTPassword: mqttPass,
        PostgresURL:  getRequiredEnv("POSTGRES_URL"),
        RedisURL:     getEnv("REDIS_URL"),
        LogLevel:     getRequiredEnv("LOG_LEVEL"),
    }
}

func getEnv(key string) string {
    return strings.TrimSpace(os.Getenv(key))
}

func getRequiredEnv(key string) string {
    value := os.Getenv(key)
    if strings.TrimSpace(value) == "" {
        panic("required environment variable is not set: " + key)
    }
    return value
}

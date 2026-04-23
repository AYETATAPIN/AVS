package config

import (
    "os"
    "strconv"
    "strings"
)

type Config struct {
    HTTPPort     int
    MQTTBroker   string
    MQTTUsername string
    MQTTPassword string
    LogLevel     string
    CommandTimeoutSec int 
}

func Load() *Config {
    return &Config{
        HTTPPort:          getRequiredEnvAsInt("HTTP_PORT"),
        MQTTBroker:        getRequiredEnv("MQTT_BROKER"),
        MQTTUsername:      getEnv("MQTT_USERNAME"),
        MQTTPassword:      getEnv("MQTT_PASSWORD"),
        LogLevel:          getRequiredEnv("LOG_LEVEL"),
        CommandTimeoutSec: getEnvAsInt("COMMAND_TIMEOUT_SEC", 30), // по умолчанию 30
    }
}

// вспомогательная функция с дефолтом
func getEnvAsInt(key string, defaultValue int) int {
    if v := strings.TrimSpace(os.Getenv(key)); v != "" {
        if i, err := strconv.Atoi(v); err == nil {
            return i
        }
    }
    return defaultValue
}

func getEnv(key string) string {
	return strings.TrimSpace(os.Getenv(key))
}

func getRequiredEnv(key string) string {
    if v := os.Getenv(key); strings.TrimSpace(v) != "" {
        return v
    }
    panic("required environment variable is not set: " + key)
}

func getRequiredEnvAsInt(key string) int {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
        if i, err := strconv.Atoi(v); err == nil {
            return i
        }
		panic("required environment variable is not a valid integer: " + key)
    }
	panic("required environment variable is not set: " + key)
}
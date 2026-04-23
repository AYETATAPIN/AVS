package storage

import (
    "context"
    "log"
    "time"

    "github.com/go-redis/redis/v8"
)

type RedisClient struct {
    Client *redis.Client
    Ctx    context.Context
}

func NewRedisClient(redisURL string) *RedisClient {
    opts, err := redis.ParseURL(redisURL)
    if err != nil {
        log.Fatalf("Failed to parse Redis URL: %v", err)
    }

    client := redis.NewClient(opts)
    ctx := context.Background()

    // Проверка подключения
    if err := client.Ping(ctx).Err(); err != nil {
        log.Fatalf("Failed to connect to Redis: %v", err)
    }

    log.Println("Redis connection established")
    return &RedisClient{
        Client: client,
        Ctx:    ctx,
    }
}

func (r *RedisClient) Close() {
    if err := r.Client.Close(); err != nil {
        log.Printf("Error closing Redis connection: %v", err)
    }
}

func (r *RedisClient) SetDeviceData(deviceID string, data []byte, expiration time.Duration) error {
    key := "device:" + deviceID
    return r.Client.Set(r.Ctx, key, data, expiration).Err()
}

func (r *RedisClient) GetDeviceData(deviceID string) (string, error) {
    key := "device:" + deviceID
    return r.Client.Get(r.Ctx, key).Result()
}

func (r *RedisClient) SetDeviceStatus(deviceID string, status string) error {
    key := "status:" + deviceID
    return r.Client.Set(r.Ctx, key, status, time.Hour).Err()
}
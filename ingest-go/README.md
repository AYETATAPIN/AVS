# AVS Ingest Service

Микросервис для приема данных от IoT датчиков через MQTT и сохранения в PostgreSQL.

## Требования
- Go 1.25.1
- PostgreSQL 14+
- MQTT брокер (Mosquitto)

## Установка
Установить зависимости:
1. make deps

Настроить переменные окружения:    
# Отредактировать .env файл
2. cp .env.example .env  

## Запуск
make run
или
make build
./ingest-go
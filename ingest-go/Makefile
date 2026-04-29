.PHONY: run build test clean docker-up docker-down

BINARY_NAME=ingest-go
VERSION?=1.0.0

run:
	go run ./cmd/ingest-go

build:
	go build -o $(BINARY_NAME) ./cmd/ingest-go

clean:
	rm -f $(BINARY_NAME)
	go clean

test:
	go test ./...

docker-up:
	docker-compose up -d mqtt

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

deps:
	go mod tidy
	go mod download

fmt:
	go fmt ./...

lint:
	golangci-lint run

check-connection:
	@echo "🔍 Проверка подключений..."
	@echo -n "MQTT (1883): "
	@nc -zv localhost 1883 2>&1 | grep -q "succeeded" && echo "success" || echo "error"
	@echo -n "PostgreSQL партнера: "
	@timeout 2 psql $(POSTGRES_URL) -c "SELECT 1;" 2>&1 | grep -q "1 row" && echo "success" || echo "error"

help:
	@echo "Доступные команды:"
	@echo "  make run           - Запустить сервис"
	@echo "  make build         - Собрать бинарник"
	@echo "  make docker-up     - Запустить MQTT брокер"
	@echo "  make docker-down   - Остановить контейнеры"
	@echo "  make deps          - Установить зависимости"
	@echo "  make check         - Проверить подключения"
	@echo "  make clean         - Очистить сборочные файлы"

package mqtt

import (
	"sync"

	"device-go/internal/models"
)

// ResponseWaiter управляет ожидающими ответа командами.
type ResponseWaiter struct {
	mu      sync.Mutex
	waiters map[string]chan *models.MQTTResponse
}

// NewResponseWaiter создаёт новый экземпляр.
func NewResponseWaiter() *ResponseWaiter {
	return &ResponseWaiter{
		waiters: make(map[string]chan *models.MQTTResponse),
	}
}

// Register создаёт канал для commandID и возвращает его.
func (rw *ResponseWaiter) Register(commandID string) <-chan *models.MQTTResponse {
	rw.mu.Lock()
	defer rw.mu.Unlock()
	ch := make(chan *models.MQTTResponse, 1)
	rw.waiters[commandID] = ch
	return ch
}

// Deliver отправляет ответ ожидающему (если есть).
func (rw *ResponseWaiter) Deliver(resp *models.MQTTResponse) {
	rw.mu.Lock()
	ch, ok := rw.waiters[resp.CommandID]
	if ok {
		delete(rw.waiters, resp.CommandID)
	}
	rw.mu.Unlock()

	if ok {
		select {
		case ch <- resp:
		default:
			// Канал уже закрыт или не готов – игнорируем
		}
	}
}

// Unregister удаляет ожидание и закрывает канал (по таймауту).
func (rw *ResponseWaiter) Unregister(commandID string) {
	rw.mu.Lock()
	ch, ok := rw.waiters[commandID]
	if ok {
		delete(rw.waiters, commandID)
		close(ch)
	}
	rw.mu.Unlock()
}
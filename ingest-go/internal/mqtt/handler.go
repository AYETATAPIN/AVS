package mqtt

import (
	"encoding/json"
	"log"
	"runtime"
	"strings"
	"sync"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"ingest-go/internal/models"
	"ingest-go/internal/storage"
)

type Handler struct {
	db    *storage.PostgresDB
	redis *storage.RedisClient
	jobs  chan pendingMsg
	wg    sync.WaitGroup
}

type pendingMsg struct {
	payload []byte
	msg     mqtt.Message
}

const (
	workerQueueSize = 50000
	minWorkers      = 4
	batchMaxRows  = 500
	batchInterval = 200 * time.Millisecond
)

type redisRecord struct {
	ID           uint      `json:"id"`
	SensorID     string    `json:"sensorId"`
	BuildingName string    `json:"buildingName"`
	RoomNumber   string    `json:"roomNumber"`
	TS           time.Time `json:"ts"`
	CO2          int       `json:"co2"`
	Temperature  int       `json:"temperature"`
	Humidity     int       `json:"humidity"`
}

func NewHandler(db *storage.PostgresDB, redis *storage.RedisClient) *Handler {
	h := &Handler{
		db:    db,
		redis: redis,
		jobs:  make(chan pendingMsg, workerQueueSize),
	}

	workers := runtime.NumCPU() * 4
	if workers < minWorkers {
		workers = minWorkers
	}
	for i := 0; i < workers; i++ {
		h.wg.Add(1)
		go h.batchWorker()
	}

	return h
}

func (h *Handler) Close() {
	close(h.jobs)
	h.wg.Wait()
}

func (h *Handler) HandleMessage(client mqtt.Client, msg mqtt.Message) {
	topic := msg.Topic()

	switch {
	case strings.HasPrefix(topic, "sensors/") && strings.HasSuffix(topic, "/data"):
		payload := append([]byte(nil), msg.Payload()...)
		h.jobs <- pendingMsg{payload: payload, msg: msg}
	case strings.HasPrefix(topic, "sensors/") && strings.HasSuffix(topic, "/status"):
		h.handleSensorStatus(msg.Payload())
		msg.Ack()
	case strings.HasPrefix(topic, "commands/"):
		h.handleCommand(msg.Payload())
		msg.Ack()
	default:
		msg.Ack()
	}
}

func (h *Handler) batchWorker() {
	defer h.wg.Done()

	rows := make([]models.SensorData, 0, batchMaxRows)
	pendingAcks := make([]mqtt.Message, 0, batchMaxRows)
	ticker := time.NewTicker(batchInterval)
	defer ticker.Stop()

	flush := func() {
		if len(rows) == 0 {
			return
		}
		h.flushBatch(rows, pendingAcks)
		rows = rows[:0]
		pendingAcks = pendingAcks[:0]
	}

	for {
		select {
		case job, ok := <-h.jobs:
			if !ok {
				flush()
				return
			}
			row, parsed := parseSensorPayload(job.payload)
			if !parsed {
				job.msg.Ack()
				continue
			}
			rows = append(rows, row)
			pendingAcks = append(pendingAcks, job.msg)
			if len(rows) >= batchMaxRows {
				flush()
			}
		case <-ticker.C:
			flush()
		}
	}
}

func (h *Handler) flushBatch(rows []models.SensorData, acks []mqtt.Message) {
	if err := h.db.CreateSensorDataBatch(rows); err != nil {
		log.Printf("Error saving sensor batch (%d rows) to PostgreSQL: %v", len(rows), err)
		for _, m := range acks {
			m.Ack()
		}
		return
	}

	if h.redis != nil {
		current := make(map[string][]byte, len(rows))
		for i := range rows {
			rec := redisRecord{
				ID:           rows[i].ID,
				SensorID:     rows[i].SensorID,
				BuildingName: rows[i].BuildingName,
				RoomNumber:   rows[i].RoomNumber,
				TS:           rows[i].TS,
				CO2:          rows[i].CO2,
				Temperature:  rows[i].Temperature,
				Humidity:     rows[i].Humidity,
			}
			if b, err := json.Marshal(rec); err == nil {
				current[rows[i].SensorID] = b
			}
		}
		if len(current) > 0 {
			if err := h.redis.SetCurrentSensorRecordsBatch(current); err != nil {
				log.Printf("Error writing Redis batch (%d entries): %v", len(current), err)
			}
		}
	}

	for i := range rows {
		log.Printf("Saved: %s (%s, %s) - CO2: %dppm, Temp: %d°C, Humidity: %d%%",
			rows[i].SensorID, rows[i].BuildingName, rows[i].RoomNumber,
			rows[i].CO2, rows[i].Temperature, rows[i].Humidity)
	}

	for _, m := range acks {
		m.Ack()
	}
}

func parseSensorPayload(payload []byte) (models.SensorData, bool) {
	var mqttMsg models.MQTTMessage
	if err := json.Unmarshal(payload, &mqttMsg); err != nil {
		log.Printf("Error parsing sensor data JSON: %v", err)
		log.Printf("Raw payload: %s", string(payload))
		return models.SensorData{}, false
	}
	data := models.SensorData{
		SensorID:     mqttMsg.SensorID,
		BuildingName: models.GetRussianBuildingName(mqttMsg.BuildingName),
		RoomNumber:   models.ConvertRoomNumber(mqttMsg.RoomNumber),
		TS:           mqttMsg.TS,
		CO2:          mqttMsg.CO2,
		Temperature:  mqttMsg.Temperature,
		Humidity:     mqttMsg.Humidity,
	}
	if data.TS.IsZero() {
		data.TS = time.Now()
	}
	return data, true
}

func (h *Handler) handleSensorStatus(payload []byte) {
	log.Printf("Sensor status: %s", string(payload))
}

func (h *Handler) handleCommand(payload []byte) {
	log.Printf("Command received: %s", string(payload))
}

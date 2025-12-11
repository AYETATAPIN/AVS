package models

import "time"

// SensorData - соответствует таблице sensors в PostgreSQL
type SensorData struct {
    ID           uint      `gorm:"primaryKey;column:id" json:"id"`
    SensorID     string    `gorm:"column:sensor_id;not null" json:"sensor_id"`
    BuildingName string    `gorm:"column:building_name;not null" json:"building_name"`
    RoomNumber   string    `gorm:"column:room_number;not null" json:"room_number"`
    TS           time.Time `gorm:"column:ts;not null;default:now()" json:"ts"`
    CO2          int       `gorm:"column:co2;not null;default:1" json:"co2"`
    Temperature  int       `gorm:"column:temperature;not null;default:1" json:"temperature"`
    Humidity     int       `gorm:"column:humidity;not null;default:1" json:"humidity"`
}

// TableName - указывает имя таблицы в БД
func (SensorData) TableName() string {
    return "sensors"
}

// MQTTMessage - структура входящего MQTT сообщения
type MQTTMessage struct {
    SensorID     string    `json:"sensorId"`
    BuildingName string    `json:"buildingName"`
    RoomNumber   string    `json:"roomNumber"`
    TS           time.Time `json:"ts"`
    CO2          int       `json:"co2"`
    Temperature  int       `json:"temperature"`
    Humidity     int       `json:"humidity"`
}
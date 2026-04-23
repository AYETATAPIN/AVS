package models

import (
    "strings"
    "time"
)

// BuildingMapping - соответствие английских названий русским
var BuildingMapping = map[string]string{
    "Auditory":               "Аудиторный корпус",
    "Main":                   "Главный корпус",
    "Educational_Laboratory": "Учебно-лабораторный корпус",
    "Educational_1":          "Учебный корпус №1",
    "Rectorate":              "Ректорат",
}

// LetterMapping - соответствие английских букв русским
var LetterMapping = map[string]string{
    "a": "а",  // английская a -> русская а
    "b": "б",  // английская b -> русская б  
    "k": "к",  // английская k -> русская к
    "c": "с",  // на всякий случай
    "e": "е",  // английская e -> русская е
    "m": "м",  // английская m -> русская м
    "o": "о",  // английская o -> русская о
    "p": "р",  // английская p -> русская р
    "t": "т",  // английская t -> русская т
    "x": "х",  // английская x -> русская х
    "y": "у",  // английская y -> русская у
}

// GetRussianBuildingName - преобразует английское название в русское
func GetRussianBuildingName(englishName string) string {
    if russianName, ok := BuildingMapping[englishName]; ok {
        return russianName
    }
    return englishName
}

// ConvertRoomNumber - преобразует английские буквы в номере комнаты на русские
func ConvertRoomNumber(roomNumber string) string {
    if len(roomNumber) == 0 {
        return roomNumber
    }
    
    // Получаем последний символ
    lastChar := roomNumber[len(roomNumber)-1:]
    
    // Проверяем, является ли последний символ английской буквой
    if russianLetter, ok := LetterMapping[strings.ToLower(lastChar)]; ok {
        // Заменяем последнюю букву на русскую
        // Сохраняем регистр
        if strings.ToUpper(lastChar) == lastChar {
            // Если была заглавная английская, делаем заглавную русскую
            return roomNumber[:len(roomNumber)-1] + strings.ToUpper(russianLetter)
        } else {
            // Если была строчная английская, делаем строчную русскую
            return roomNumber[:len(roomNumber)-1] + russianLetter
        }
    }
    
    return roomNumber
}

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

// TableName - ЯВНО указываем имя таблицы
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
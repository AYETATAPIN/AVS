package models

import (
    "strings"
)

// BuildingMapping - соответствие русских названий английским (обратное тому, что в ingest-go)
var buildingMapping = map[string]string{
    "Аудиторный корпус":          "Auditory",
    "Главный корпус":             "Main",
    "Учебно-лабораторный корпус": "Educational_Laboratory",
    "Учебный корпус №1":          "Educational_1",
    "Ректорат":                   "Rectorate",
}

// letterMapping - русская буква -> английская (только для замены последней буквы)
var letterMapping = map[string]string{
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

// ConvertBuildingToEnglish преобразует русское название здания в английское
func ConvertBuildingToEnglish(russianName string) string {
    if english, ok := buildingMapping[russianName]; ok {
        return english
    }
    return russianName // если не найдено, оставляем как есть
}

// ConvertRoomNumberToEnglish преобразует номер комнаты: заменяет последнюю русскую букву на английскую
func ConvertRoomNumberToEnglish(roomNumber string) string {
    if len(roomNumber) == 0 {
        return roomNumber
    }
    lastChar := string([]rune(roomNumber)[len([]rune(roomNumber))-1])
    if english, ok := letterMapping[strings.ToLower(lastChar)]; ok {
        // сохраняем регистр исходной буквы
        if lastChar == strings.ToUpper(lastChar) {
            return roomNumber[:len(roomNumber)-1] + strings.ToUpper(english)
        }
        return roomNumber[:len(roomNumber)-1] + english
    }
    return roomNumber
}
package storage

import (
    "time"

    "ingest-go/models"
    "gorm.io/driver/postgres"
    "gorm.io/gorm"
    "gorm.io/gorm/schema" // Добавляем этот импорт
)

type PostgresDB struct {
    db *gorm.DB
}

func NewPostgres(dsn string) (*PostgresDB, error) {
    db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
        // Настройка именования таблиц
        NamingStrategy: schema.NamingStrategy{
            TablePrefix:   "",
            SingularTable: false, // false = plural (sensors), true = singular (sensor)
        },
    })
    if err != nil {
        return nil, err
    }
    
    // Настраиваем пул соединений
    sqlDB, err := db.DB()
    if err != nil {
        return nil, err
    }
    
    sqlDB.SetMaxIdleConns(10)
    sqlDB.SetMaxOpenConns(100)
    sqlDB.SetConnMaxLifetime(time.Hour)
    
    // Создаем таблицу если не существует
    if err := db.AutoMigrate(&models.SensorData{}); err != nil {
        return nil, err
    }
    
    // Создаем индексы
    db.Exec("CREATE INDEX IF NOT EXISTS idx_sensors_sensor_id ON sensors(sensor_id);")
    db.Exec("CREATE INDEX IF NOT EXISTS idx_sensors_ts ON sensors(ts);")
    db.Exec("CREATE INDEX IF NOT EXISTS idx_sensors_room ON sensors(room_number);")
    
    return &PostgresDB{db: db}, nil
}

func (p *PostgresDB) CreateSensorData(data *models.SensorData) error {
    return p.db.Create(data).Error
}

func (p *PostgresDB) GetLatestSensorData(sensorID string, limit int) ([]models.SensorData, error) {
    var data []models.SensorData
    err := p.db.Where("sensor_id = ?", sensorID).
        Order("ts DESC").
        Limit(limit).
        Find(&data).Error
    return data, err
}

func (p *PostgresDB) GetDataInTimeRange(sensorID string, from, to time.Time) ([]models.SensorData, error) {
    var data []models.SensorData
    err := p.db.Where("sensor_id = ? AND ts BETWEEN ? AND ?", sensorID, from, to).
        Order("ts ASC").
        Find(&data).Error
    return data, err
}

func (p *PostgresDB) Close() error {
    sqlDB, err := p.db.DB()
    if err != nil {
        return err
    }
    return sqlDB.Close()
}
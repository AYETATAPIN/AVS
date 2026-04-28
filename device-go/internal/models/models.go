package models

// Список поддерживаемых команд
const (
    CmdReboot        = "reboot"
    CmdGetSensors    = "get_sensors"
    CmdGetBattery    = "get_battery"
    CmdOTAUpdate     = "ota_update"
    CmdOTARollback   = "ota_rollback"
    CmdGetVersion    = "get_version"
    CmdSetLocation   = "set_location"
    CmdEnableFallDet = "enable_fall_detection"
    CmdGetOrientation = "get_orientation"
    CmdPowerOn       = "power_on"   
    CmdPowerOff      = "power_off"  
    CmdRegister      = "register"    
)

// AllCommands возвращает список всех доступных команд
func AllCommands() []string {
    return []string{
        CmdReboot,
        CmdGetSensors,
        CmdGetBattery,
        CmdOTAUpdate,
        CmdOTARollback,
        CmdGetVersion,
        CmdSetLocation,
        CmdEnableFallDet,
        CmdGetOrientation,
        CmdPowerOn,
        CmdPowerOff,
        CmdRegister,
    }
}

// CommandRequest — тело запроса на отправку команды
type CommandRequest struct {
    DeviceID   string         `json:"device_id"`
    Command    string         `json:"command"`
    Parameters map[string]any `json:"parameters"`
}

// CommandResponse — ответ после отправки команды
type CommandResponse struct {
    CommandID string `json:"command_id"`
    Status    string `json:"status"` // "sent"
}

// MQTTCommand — структура команды для публикации в MQTT
type MQTTCommand struct {
    CommandID  string         `json:"command_id"`
    Command    string         `json:"command"`
    Parameters map[string]any `json:"parameters"`
}

// MQTTResponse — структура ответа от устройства (для логирования)
type MQTTResponse struct {
    CommandID string         `json:"command_id"`
    Status    string         `json:"status"` // "success" / "failed"
    Data      map[string]any `json:"data"`
    Firmware  string         `json:"firmware_version,omitempty"`
    Battery   float64        `json:"battery,omitempty"`
    WiFi      int            `json:"wifi_signal,omitempty"`
}
package com.avs.api_java.controller;

import com.avs.api_java.service.DeviceCommandService;
import com.avs.api_java.jpa_repository.ApiRepository;
import com.avs.api_java.redis.CurrentStateRedisService;
import com.avs.api_java.entity.RecordEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

@RestController
@CrossOrigin(origins = "*")
@RequestMapping("/api/admin/commands")
public class AdminCommandController {
    private final DeviceCommandService deviceCommandService;
    private final ApiRepository apiRepository;
    private final CurrentStateRedisService currentStateRedisService;

    public AdminCommandController(DeviceCommandService deviceCommandService, 
                                  ApiRepository apiRepository, 
                                  CurrentStateRedisService currentStateRedisService) {
        this.deviceCommandService = deviceCommandService;
        this.apiRepository = apiRepository;
        this.currentStateRedisService = currentStateRedisService;
    }

    @PostMapping
    public ResponseEntity<String> sendCommand(@RequestBody Map<String, Object> commandPayload) {
        String command = (String) commandPayload.get("command");
        String sensorId = (String) commandPayload.get("device_id");

        if ("unbind".equals(command)) {
            try {
                deviceCommandService.forwardCommand(commandPayload);
            } catch (Exception e) {
            }

            RecordEntity unbindRecord = new RecordEntity();
            unbindRecord.setSensorId(sensorId);
            unbindRecord.setBuildingName("");
            unbindRecord.setRoomNumber("");
            unbindRecord.setTs(Instant.now());
            unbindRecord.setCo2(0);
            unbindRecord.setTemperature(0);
            unbindRecord.setHumidity(0);
            apiRepository.save(unbindRecord);

            currentStateRedisService.deleteSensor(sensorId);

            return ResponseEntity.ok("{\"status\":\"success\",\"message\":\"Successfully unbound sensor\"}");
        }

        return deviceCommandService.forwardCommand(commandPayload);
    }
}

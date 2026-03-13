package com.avs.api_java.controller;

import com.avs.api_java.service.DeviceCommandService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@CrossOrigin(origins = "*")
@RequestMapping("/api/admin/commands")
public class AdminCommandController {
    private final DeviceCommandService deviceCommandService;

    public AdminCommandController(DeviceCommandService deviceCommandService) {
        this.deviceCommandService = deviceCommandService;
    }

    @PostMapping
    public ResponseEntity<String> sendCommand(@RequestBody Map<String, Object> commandPayload) {
        return deviceCommandService.forwardCommand(commandPayload);
    }
}

package com.avs.api_java.controller;

import com.avs.api_java.entity.RecordEntity;
import com.avs.api_java.service.ApiService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;

@RestController
@CrossOrigin(origins = "*")
@RequestMapping("/api/sensors")
public class ApiController {
    private final ApiService service;
    public ApiController(ApiService service){
        this.service=service;
    }

    @GetMapping("/current")
    public List<RecordEntity> getCurrent(){
        return service.getCurrentState();
    }

    @GetMapping("/{sensorId}/history")
    public List<RecordEntity> getHistory(@PathVariable String sensorId, @RequestParam Instant from, @RequestParam Instant to) {
        return service.getSensorHistory(sensorId, from, to);
    }
}

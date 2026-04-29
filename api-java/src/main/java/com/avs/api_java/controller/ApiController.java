package com.avs.api_java.controller;

import com.avs.api_java.entity.RecordEntity;
import com.avs.api_java.service.ApiService;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

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

    @GetMapping("/{sensorId}/history/aggregated")
    public List<RecordEntity> getHistoryAggregated(
            @PathVariable String sensorId,
            @RequestParam Instant from,
            @RequestParam Instant to,
            @RequestParam(defaultValue = "3600") long intervalSeconds) {
        return service.getSensorHistoryAggregated(sensorId, from, to, intervalSeconds);
    }
}

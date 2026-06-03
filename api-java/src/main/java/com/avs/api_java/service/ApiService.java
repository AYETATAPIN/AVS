package com.avs.api_java.service;

import com.avs.api_java.entity.RecordEntity;
import com.avs.api_java.jpa_repository.ApiRepository;
import com.avs.api_java.redis.CurrentStateRedisService;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ApiService {
    private final ApiRepository repo;
    private final CurrentStateRedisService currentStateRedisService;

    public ApiService(ApiRepository repo, CurrentStateRedisService currentStateRedisService){
        this.repo=repo;
        this.currentStateRedisService = currentStateRedisService;
    }

    public List<RecordEntity> getCurrentState() {
        List<RecordEntity> activeSensors;
        try {
            activeSensors = currentStateRedisService.getCurrentState();
            if (activeSensors.isEmpty()) {
                activeSensors = repo.getCurrent();
            }
        } catch (DataAccessException ignored) {
            activeSensors = repo.getCurrent();
        }

        for (RecordEntity sensor : activeSensors) {
            sensor.setActive(true);
        }
        return activeSensors;
    }

    public List<RecordEntity> getSensorHistoryAggregated(String sensorId, Instant from, Instant to, long intervalSeconds) {
        return repo.getHistoryAggregated(sensorId, from, to, intervalSeconds).stream().map(row -> {
            RecordEntity record = new RecordEntity();
            record.setSensorId(sensorId);
            record.setTs((Instant) row[0]);
            record.setCo2(((Number) row[1]).intValue());
            record.setTemperature(((Number) row[2]).intValue());
            record.setHumidity(((Number) row[3]).intValue());
            return record;
        }).collect(Collectors.toList());
    }
}

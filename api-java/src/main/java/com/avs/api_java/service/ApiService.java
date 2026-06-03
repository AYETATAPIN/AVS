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

    private List<RecordEntity> cachedState = null;
    private long lastCacheTime = 0;
    private static final long CACHE_TTL_MS = 5000; // 5 seconds

    public ApiService(ApiRepository repo, CurrentStateRedisService currentStateRedisService){
        this.repo=repo;
        this.currentStateRedisService = currentStateRedisService;
    }

    public synchronized List<RecordEntity> getCurrentState() {
        long now = System.currentTimeMillis();
        if (cachedState != null && (now - lastCacheTime) < CACHE_TTL_MS) {
            return cachedState;
        }

        List<RecordEntity> activeSensors;
        try {
            activeSensors = currentStateRedisService.getCurrentState();
        } catch (DataAccessException ignored) {
            activeSensors = new java.util.ArrayList<>();
        }

        java.util.Map<String, String> activeSensorRooms = new java.util.HashMap<>();
        for (RecordEntity sensor : activeSensors) {
            if (sensor.getSensorId() != null && 
                sensor.getBuildingName() != null && !sensor.getBuildingName().trim().isEmpty() &&
                sensor.getRoomNumber() != null && !sensor.getRoomNumber().trim().isEmpty()) {
                activeSensorRooms.put(sensor.getSensorId(), sensor.getBuildingName() + "|" + sensor.getRoomNumber());
            }
        }

        List<RecordEntity> roomRecords = repo.getLatestRoomRecords();
        for (RecordEntity record : roomRecords) {
            String activeRoom = activeSensorRooms.get(record.getSensorId());
            String currentRoomKey = record.getBuildingName() + "|" + record.getRoomNumber();
            if (activeRoom != null && activeRoom.equals(currentRoomKey)) {
                record.setActive(true);
            } else {
                record.setActive(false);
            }
        }

        cachedState = roomRecords;
        lastCacheTime = now;
        return roomRecords;
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

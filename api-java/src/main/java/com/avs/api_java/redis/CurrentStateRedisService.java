package com.avs.api_java.redis;

import com.avs.api_java.entity.RecordEntity;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

@Service
public class CurrentStateRedisService {

    private final HashOperations<String, String, String> hashOps;
    private final ObjectMapper objectMapper;

    public CurrentStateRedisService(StringRedisTemplate redisTemplate, ObjectMapper redisObjectMapper) {
        this.hashOps = redisTemplate.opsForHash();
        this.objectMapper = redisObjectMapper;
    }

    public List<RecordEntity> getCurrentState() {
        Map<String, String> all;
        try {
            all = hashOps.entries("avs:sensors:current");
        } catch (DataAccessException e) {
            throw e;
        }

        List<RecordEntity> out = new ArrayList<>(all.size());
        for (String json : all.values()) {
            try {
                out.add(objectMapper.readValue(json, RecordEntity.class));
            } catch (Exception ignored) {
            }
        }
        out.sort(Comparator.comparing(RecordEntity::getSensorId, Comparator.nullsLast(String::compareTo)));
        return out;
    }
}


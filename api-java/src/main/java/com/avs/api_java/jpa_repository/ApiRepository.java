package com.avs.api_java.jpa_repository;

import com.avs.api_java.entity.RecordEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.List;

public interface ApiRepository extends JpaRepository<RecordEntity, Long> {
    @Query(value = """
        SELECT DISTINCT ON (sensor_id) *
        FROM sensors
        ORDER BY sensor_id, ts DESC
        """, nativeQuery = true)
    List<RecordEntity> getCurrent();

    @Query(value = """
        SELECT *
        FROM sensors
        WHERE sensor_id = :sensorId
          AND ts >= :from
          AND ts <= :to
        ORDER BY ts ASC
        """, nativeQuery = true)
    List<RecordEntity> getHistory(@Param("sensorId") String sensorId, @Param("from") Instant from, @Param("to") Instant to);
}

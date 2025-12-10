package com.avs.api_java.jpa_repository;

import com.avs.api_java.entity.RecordEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface ApiRepository extends JpaRepository<RecordEntity, Long> {
    @Query(value = """
        SELECT DISTINCT ON (sensor_id) *
        FROM sensors
        ORDER BY sensor_id, ts DESC
        """, nativeQuery = true)
    List<RecordEntity> getCurrent();
}

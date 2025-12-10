package com.avs.api_java.jpa_repository;

import com.avs.api_java.entity.AdminEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AdminRepository extends JpaRepository<AdminEntity, Long> {
        Optional<AdminEntity> findByLogin(String login);
}

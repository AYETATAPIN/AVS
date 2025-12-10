package com.avs.api_java.service;

import com.avs.api_java.entity.RecordEntity;
import com.avs.api_java.jpa_repository.ApiRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ApiService {
    private final ApiRepository repo;
    public ApiService(ApiRepository repo){
        this.repo=repo;
    }

    public List<RecordEntity> getCurrentState (){
        return repo.getCurrent();
    }
}

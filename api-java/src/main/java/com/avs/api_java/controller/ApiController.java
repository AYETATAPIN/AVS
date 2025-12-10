package com.avs.api_java.controller;

import com.avs.api_java.entity.RecordEntity;
import com.avs.api_java.service.ApiService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
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
}

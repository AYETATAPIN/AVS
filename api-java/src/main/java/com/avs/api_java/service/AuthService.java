package com.avs.api_java.service;

import com.avs.api_java.jwt_security.JwtUtil;
import com.avs.api_java.entity.AdminEntity;
import com.avs.api_java.jpa_repository.AdminRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.Objects;

@Service
public class AuthService {
    private final AdminRepository repo;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    public AuthService(AdminRepository repo, PasswordEncoder pe, JwtUtil ju){
        this.repo=repo;
        this.passwordEncoder=pe;
        this.jwtUtil=ju;
    }
    public String login(String username, String password){
        AdminEntity admin = repo.findByLogin(username).orElseThrow(() -> new RuntimeException("Admin not in database"));
        if(!(Objects.equals(password, admin.getPassword()))){
            throw new RuntimeException("Wrong password");
        }
        return jwtUtil.generateToken(username);
    }
}

package com.avs.api_java.service;

import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Map;

@Service
public class DeviceCommandService {
    private final RestTemplate restTemplate;

    @Value("${device-go.base-url}")
    private String deviceGoBasePath;

    public DeviceCommandService() {
        this.restTemplate = new RestTemplate();
    }

    @SuppressWarnings("unchecked")
    public ResponseEntity<String> forwardCommand(Map<String, Object> commandPayload) {
        String command = (String) commandPayload.get("command");
        if ("ota_update".equals(command)) {
            Map<String, Object> parameters = (Map<String, Object>) commandPayload.get("parameters");
            if (parameters != null && parameters.containsKey("url")) {
                String urlStr = (String) parameters.get("url");
                if (urlStr != null && !urlStr.trim().isEmpty()) {
                    try {
                        URL url = new URL(urlStr);
                        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                        conn.setRequestMethod("GET");
                        conn.setConnectTimeout(10000);
                        conn.setReadTimeout(30000);
                        
                        int responseCode = conn.getResponseCode();
                        if (responseCode != 200) {
                            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                                .body("{\"status\":\"failed\",\"data\":{\"error\":\"Ошибка при скачивании файла прошивки. Код ответа сервера: " + responseCode + "\"}}");
                        }
                        
                        long length = conn.getContentLengthLong();
                        MessageDigest digest = MessageDigest.getInstance("SHA-256");
                        
                        try (InputStream is = conn.getInputStream()) {
                            byte[] buffer = new byte[16384];
                            int bytesRead;
                            long totalBytes = 0;
                            while ((bytesRead = is.read(buffer)) != -1) {
                                digest.update(buffer, 0, bytesRead);
                                totalBytes += bytesRead;
                            }
                            
                            if (length <= 0) {
                                length = totalBytes;
                            }
                            
                            byte[] hashBytes = digest.digest();
                            StringBuilder hexString = new StringBuilder();
                            for (byte b : hashBytes) {
                                String hex = Integer.toHexString(0xff & b);
                                if (hex.length() == 1) hexString.append('0');
                                hexString.append(hex);
                            }
                            
                            parameters.put("sha256", hexString.toString());
                            parameters.put("length", length);
                        }
                    } catch (Exception e) {
                        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                            .body("{\"status\":\"failed\",\"data\":{\"error\":\"Ошибка при расчете SHA256 прошивки: " + e.getMessage() + "\"}}");
                    }
                }
            }
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> request = new HttpEntity<>(commandPayload, headers);
        try {
            return restTemplate.exchange(deviceGoBasePath + "/api/commands", HttpMethod.POST, request, String.class);
        } catch (HttpStatusCodeException ex) {
            return ResponseEntity.status(ex.getStatusCode()).body(ex.getResponseBodyAsString());
        } catch (ResourceAccessException ex) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body("{\"error\":\"device-go unavailable\"}");
        }
    }
}

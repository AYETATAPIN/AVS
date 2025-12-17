@echo off

cd /d "%~dp0"
:: -------------------------

start "ingest-go" cmd /k "docker-compose up -d && timeout /t 10 && cd ingest-go && go run main.go"

start "api-java" cmd /k "cd api-java && gradlew.bat bootRun"

start "frontend" cmd /k "cd frontend && python -m http.server 8000"
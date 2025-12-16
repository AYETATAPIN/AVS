wt `
  new-tab -d . --title "ingest-go" powershell -NoExit -Command "docker-compose up -d; Start-Sleep -Seconds 10; cd ingest-go; make run" `
  new-tab -d . --title "api-java" powershell -NoExit -Command "cd api-java; ./gradlew bootRun" `
  new-tab -d . --title "frontend" powershell -NoExit -Command "cd frontend; python -m http.server 8000"

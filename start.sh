#!/bin/sh

gnome-terminal \
  --tab --title="ingest-go" \
    --command="bash -c 'docker-compose up -d && sleep 10 && cd ingest-go && make run; exec bash'" \
  --tab --title="api-java" \
    --command="bash -c 'cd api-java && chmod +x gradlew && ./gradlew bootRun; exec bash'" \
  --tab --title="frontend" \
    --command="bash -c 'cd frontend && python3 -m http.server 8000; exec bash'"

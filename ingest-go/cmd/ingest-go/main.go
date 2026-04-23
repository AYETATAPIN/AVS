package main

import (
    "log"
    "ingest-go/internal/app"
    "ingest-go/internal/config"
)

func main() {
    cfg := config.Load()
    if err := app.Run(cfg); err != nil {
        log.Fatal(err)
    }
}
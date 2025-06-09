package main

import (
	"context"
	"log"

	"github.com/ai-gateway/ai-gateway-go/internal/config"
	"github.com/ai-gateway/ai-gateway-go/internal/server"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	srv := server.New(cfg)
	if err := srv.Start(context.Background()); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/ai-gateway/ai-gateway-go/internal/config"
	"github.com/ai-gateway/ai-gateway-go/internal/guardrails"
	"github.com/ai-gateway/ai-gateway-go/internal/provider"
	"github.com/ai-gateway/ai-gateway-go/internal/provider/echo"
	"github.com/ai-gateway/ai-gateway-go/internal/routing"
)

type Server struct {
	cfg    *config.Config
	engine *gin.Engine
	router *routing.Router
	guards *guardrails.Guardrails
}

func New(cfg *config.Config) *Server {
	r := gin.Default()
	rt := routing.New()
	rt.Register("echo", echo.New())
	srv := &Server{cfg: cfg, engine: r, router: rt, guards: guardrails.New()}
	srv.registerRoutes()
	return srv
}

func (s *Server) registerRoutes() {
	api := s.engine.Group("/v1")
	api.POST("/chat/completions", s.chatCompletion)
	api.POST("/embeddings", s.embeddings)
	api.GET("/models", s.listModels)
}

func (s *Server) Start(ctx context.Context) error {
	srv := &http.Server{
		Addr:    s.cfg.Address,
		Handler: s.engine,
	}
	go func() {
		<-ctx.Done()
		_ = srv.Shutdown(context.Background())
	}()
	return srv.ListenAndServe()
}

func (s *Server) chatCompletion(c *gin.Context) {
	var req provider.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}
	if len(req.Messages) > 0 {
		last := req.Messages[len(req.Messages)-1]
		if err := s.guards.CheckInput(last.Content); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
	}
	prov := s.router.ProviderFor(req.Model)
	stream, err := prov.Chat(c.Request.Context(), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if req.Stream {
		c.Writer.Header().Set("Content-Type", "text/event-stream")
		c.Writer.Header().Set("Cache-Control", "no-cache")
		c.Writer.Flush()
		enc := json.NewEncoder(c.Writer)
		for msg := range stream {
			if err := enc.Encode(msg); err != nil {
				break
			}
			fmt.Fprint(c.Writer, "\n")
			c.Writer.Flush()
		}
	} else {
		var msgs []provider.Message
		for m := range stream {
			msgs = append(msgs, m)
		}
		c.JSON(http.StatusOK, gin.H{"choices": msgs})
	}
}

func (s *Server) embeddings(c *gin.Context) {
	c.JSON(200, gin.H{"message": "not implemented"})
}

func (s *Server) listModels(c *gin.Context) {
	c.JSON(200, gin.H{"models": s.router.Models()})
}

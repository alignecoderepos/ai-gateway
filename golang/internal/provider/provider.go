package provider

import "context"

// Message represents a chat message.
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatRequest mirrors the OpenAI chat completion request.
type ChatRequest struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream,omitempty"`
}

// Provider handles LLM operations.
type Provider interface {
	Chat(ctx context.Context, req *ChatRequest) (<-chan Message, error)
}

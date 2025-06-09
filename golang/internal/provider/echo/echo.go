package echo

import (
	"context"

	"github.com/ai-gateway/ai-gateway-go/internal/provider"
)

// Provider responds by echoing the last user message.
type Provider struct{}

func New() *Provider { return &Provider{} }

func (p *Provider) Chat(ctx context.Context, req *provider.ChatRequest) (<-chan provider.Message, error) {
	ch := make(chan provider.Message, 1)
	go func() {
		defer close(ch)
		if len(req.Messages) == 0 {
			return
		}
		last := req.Messages[len(req.Messages)-1]
		ch <- provider.Message{Role: "assistant", Content: "Echo: " + last.Content}
	}()
	return ch, nil
}

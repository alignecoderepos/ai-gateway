package routing

import (
	"testing"

	"github.com/ai-gateway/ai-gateway-go/internal/provider/echo"
)

func TestRouterProvider(t *testing.T) {
	r := New()
	p := echo.New()
	r.Register("echo", p)
	if r.ProviderFor("echo") == nil {
		t.Fatalf("expected provider")
	}
}

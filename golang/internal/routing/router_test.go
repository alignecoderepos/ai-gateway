package routing

import (
        "io/ioutil"
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

func TestLoadFromFile(t *testing.T) {
        data := []byte("- model: test-model\n- model: another")
        tmp, err := ioutil.TempFile(t.TempDir(), "models*.yaml")
        if err != nil {
                t.Fatal(err)
        }
        if _, err := tmp.Write(data); err != nil {
                t.Fatal(err)
        }
        tmp.Close()

        r := New()
        if err := r.LoadFromFile(tmp.Name()); err != nil {
                t.Fatalf("load failed: %v", err)
        }
        if len(r.Models()) != 2 {
                t.Fatalf("expected 2 models, got %d", len(r.Models()))
        }
}

package routing

import "github.com/ai-gateway/ai-gateway-go/internal/provider"

// Model describes a model and its provider weight.
type Model struct {
	Name   string
	Weight int
}

// Router maps models to providers.
type Router struct {
	models    []Model
	providers map[string]provider.Provider
	defaultP  provider.Provider
}

func New() *Router {
	return &Router{
		models:    []Model{{Name: "echo", Weight: 1}},
		providers: make(map[string]provider.Provider),
	}
}

// Register associates a model with a provider implementation.
func (r *Router) Register(model string, p provider.Provider) {
	r.providers[model] = p
	if r.defaultP == nil {
		r.defaultP = p
	}
}

// ProviderFor returns the provider for a model or the default provider.
func (r *Router) ProviderFor(model string) provider.Provider {
	if p, ok := r.providers[model]; ok {
		return p
	}
	return r.defaultP
}

func (r *Router) Select() Model {
	if len(r.models) == 0 {
		return Model{}
	}
	return r.models[0]
}

func (r *Router) Models() []Model {
	return r.models
}

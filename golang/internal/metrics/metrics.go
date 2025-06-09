package metrics

import "sync"

type Usage struct {
	mu     sync.Mutex
	tokens int
	cost   float64
}

func (u *Usage) AddTokens(n int, price float64) {
	u.mu.Lock()
	defer u.mu.Unlock()
	u.tokens += n
	u.cost += float64(n) * price
}

func (u *Usage) Cost() float64 {
	u.mu.Lock()
	defer u.mu.Unlock()
	return u.cost
}

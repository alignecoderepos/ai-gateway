package guardrails

import (
	"errors"
	"strings"
)

// Guardrails performs simple input validation.
type Guardrails struct {
	banned []string
}

func New() *Guardrails {
	return &Guardrails{banned: []string{"banned"}}
}

// CheckInput returns an error if input contains banned words.
func (g *Guardrails) CheckInput(input string) error {
	lower := strings.ToLower(input)
	for _, w := range g.banned {
		if strings.Contains(lower, w) {
			return errors.New("input violates guardrails")
		}
	}
	return nil
}

package config

import (
    "os"
    "testing"
)

func TestLoadEnv(t *testing.T) {
    os.Setenv("AIGW_ADDRESS", ":9999")
    defer os.Unsetenv("AIGW_ADDRESS")

    cfg, err := Load()
    if err != nil {
        t.Fatalf("load failed: %v", err)
    }
    if cfg.Address != ":9999" {
        t.Fatalf("expected :9999 got %s", cfg.Address)
    }
}

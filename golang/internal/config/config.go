package config

import (
	"github.com/spf13/viper"
)

type Config struct {
	Address       string `mapstructure:"address"`
	ModelsPath    string `mapstructure:"models_path"`
	TelemetryURL  string `mapstructure:"telemetry_url"`
	ClickHouseURL string `mapstructure:"clickhouse_url"`
}

func Load() (*Config, error) {
	v := viper.New()
	v.SetConfigName("config")
	v.SetConfigType("yaml")
	v.AddConfigPath(".")
	v.AddConfigPath("./config")
	v.AutomaticEnv()
	if err := v.ReadInConfig(); err != nil {
		return nil, err
	}
	var c Config
	if err := v.Unmarshal(&c); err != nil {
		return nil, err
	}
	return &c, nil
}

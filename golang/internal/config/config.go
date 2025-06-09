package config

import (
        "errors"
        "strings"

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

        // allow environment variables like AIGW_ADDRESS
        v.SetEnvPrefix("AIGW")
        v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
        v.AutomaticEnv()

        if err := v.ReadInConfig(); err != nil {
                // don't fail if config file is missing, allow env-only config
                var nf viper.ConfigFileNotFoundError
                if !errors.As(err, &nf) {
                        return nil, err
                }
        }

        var c Config
        if err := v.Unmarshal(&c); err != nil {
                return nil, err
        }
        return &c, nil
}

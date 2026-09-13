package config

import (
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	DatabaseURL    string
	WorkspaceID    string
	APIInternalURL string
	InternalToken  string
	SenderID       string
	PollInterval   time.Duration
	PollJitter     time.Duration
	BatchSize      int
}

func Load(getenv func(string) string) (Config, error) {
	required := map[string]string{
		"DATABASE_URL":         getenv("DATABASE_URL"),
		"MAILBOX_WORKSPACE_ID": getenv("MAILBOX_WORKSPACE_ID"),
		"API_INTERNAL_URL":     getenv("API_INTERNAL_URL"),
		"INTERNAL_API_TOKEN":   getenv("INTERNAL_API_TOKEN"),
	}
	var missing []string
	for name, value := range required {
		if value == "" {
			missing = append(missing, name)
		}
	}
	if len(missing) > 0 {
		sort.Strings(missing)
		return Config{}, fmt.Errorf("missing environment variables: %s", strings.Join(missing, ", "))
	}

	cfg := Config{
		DatabaseURL:    NormalizeDatabaseURL(required["DATABASE_URL"]),
		WorkspaceID:    required["MAILBOX_WORKSPACE_ID"],
		APIInternalURL: strings.TrimRight(required["API_INTERNAL_URL"], "/"),
		InternalToken:  required["INTERNAL_API_TOKEN"],
		SenderID:       getenv("SENDER_ID"),
		PollInterval:   15 * time.Second,
		PollJitter:     5 * time.Second,
		BatchSize:      10,
	}
	if cfg.SenderID == "" {
		host, _ := os.Hostname()
		cfg.SenderID = fmt.Sprintf("go-%s-%d", host, os.Getpid())
	}
	if raw := getenv("POLL_INTERVAL_SECONDS"); raw != "" {
		seconds, err := strconv.Atoi(raw)
		if err != nil || seconds <= 0 {
			return Config{}, fmt.Errorf("POLL_INTERVAL_SECONDS must be a positive integer, got %q", raw)
		}
		cfg.PollInterval = time.Duration(seconds) * time.Second
	}
	return cfg, nil
}

func NormalizeDatabaseURL(raw string) string {
	for _, driverScheme := range []string{"postgresql+asyncpg://", "postgres+asyncpg://"} {
		if rest, found := strings.CutPrefix(raw, driverScheme); found {
			return "postgresql://" + rest
		}
	}
	return raw
}

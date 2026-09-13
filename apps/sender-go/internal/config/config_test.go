package config

import (
	"strings"
	"testing"
	"time"
)

func env(values map[string]string) func(string) string {
	return func(name string) string { return values[name] }
}

func completeEnv() map[string]string {
	return map[string]string{
		"DATABASE_URL":         "postgresql+asyncpg://outboxlab:outboxlab@postgres:5432/outboxlab",
		"MAILBOX_WORKSPACE_ID": "019e5f2a-1a6d-7fa2-8bee-55d3e1ccdc3d",
		"API_INTERNAL_URL":     "http://api:8000/",
		"INTERNAL_API_TOKEN":   "token",
	}
}

func TestLoadNormalizesTheSharedDatabaseURLAndAppliesDefaults(t *testing.T) {
	cfg, err := Load(env(completeEnv()))
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if cfg.DatabaseURL != "postgresql://outboxlab:outboxlab@postgres:5432/outboxlab" {
		t.Errorf("DatabaseURL = %q", cfg.DatabaseURL)
	}
	if cfg.APIInternalURL != "http://api:8000" {
		t.Errorf("APIInternalURL = %q", cfg.APIInternalURL)
	}
	if cfg.PollInterval != 15*time.Second || cfg.BatchSize != 10 {
		t.Errorf("defaults = %v, %d", cfg.PollInterval, cfg.BatchSize)
	}
	if !strings.HasPrefix(cfg.SenderID, "go-") {
		t.Errorf("SenderID = %q", cfg.SenderID)
	}
}

func TestLoadListsEveryMissingVariable(t *testing.T) {
	_, err := Load(env(map[string]string{"DATABASE_URL": "postgresql://x"}))
	if err == nil {
		t.Fatal("expected an error")
	}
	want := "missing environment variables: API_INTERNAL_URL, INTERNAL_API_TOKEN, MAILBOX_WORKSPACE_ID"
	if err.Error() != want {
		t.Errorf("error = %q", err)
	}
}

func TestLoadRejectsABadPollInterval(t *testing.T) {
	values := completeEnv()
	values["POLL_INTERVAL_SECONDS"] = "0"
	if _, err := Load(env(values)); err == nil {
		t.Fatal("expected an error")
	}
}

func TestNormalizeKeepsAPlainPostgresURL(t *testing.T) {
	raw := "postgresql://user:pass@host/db?sslmode=require"
	if got := NormalizeDatabaseURL(raw); got != raw {
		t.Errorf("NormalizeDatabaseURL = %q", got)
	}
}

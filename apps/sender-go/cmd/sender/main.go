package main

import (
	"context"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/selivanov-tech/outboxlab/apps/sender-go/internal/api"
	"github.com/selivanov-tech/outboxlab/apps/sender-go/internal/config"
	"github.com/selivanov-tech/outboxlab/apps/sender-go/internal/queue"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	if err := run(logger); err != nil {
		logger.Error("sender stopped", "error", err)
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	cfg, err := config.Load(os.Getenv)
	if err != nil {
		return err
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		return fmt.Errorf("connect to database: %w", err)
	}
	defer pool.Close()

	client := api.NewClient(cfg.APIInternalURL, cfg.InternalToken, &http.Client{Timeout: time.Minute})
	logger.Info("sender started", "sender_id", cfg.SenderID, "workspace_id", cfg.WorkspaceID, "api", cfg.APIInternalURL)

	for {
		drain(ctx, logger, pool, client, cfg)
		wait := cfg.PollInterval + time.Duration(rand.Int64N(int64(cfg.PollJitter)+1))
		select {
		case <-ctx.Done():
			logger.Info("sender stopping")
			return nil
		case <-time.After(wait):
		}
	}
}

func drain(ctx context.Context, logger *slog.Logger, pool *pgxpool.Pool, client *api.Client, cfg config.Config) {
	var jobs []queue.Job
	err := pgx.BeginFunc(ctx, pool, func(tx pgx.Tx) error {
		claimed, err := queue.Claim(ctx, tx, queue.ClaimRequest{
			WorkspaceID: cfg.WorkspaceID,
			WorkerID:    cfg.SenderID,
			Limit:       cfg.BatchSize,
			Moment:      time.Now().UTC(),
		})
		jobs = claimed
		return err
	})
	if err != nil {
		if ctx.Err() == nil {
			logger.Error("claim failed", "error", err)
		}
		return
	}

	for _, job := range jobs {
		started := time.Now()
		attributes := []any{
			"job_id", job.ID,
			"lead_id", job.LeadID,
			"step_position", job.Payload.StepPosition,
			"attempt", job.Attempts,
			"queue_latency_ms", started.Sub(job.ScheduledAt).Milliseconds(),
		}
		if job.PayloadError != nil {
			logger.Error("send job payload does not match the v1 contract; it stays claimed until the lease expires",
				append(attributes, "error", job.PayloadError)...)
			continue
		}
		result, err := client.ProcessSendJob(ctx, job.WorkspaceID, job.ID)
		attributes = append(attributes, "duration_ms", time.Since(started).Milliseconds())
		if err != nil {
			logger.Error("send job not processed; it is claimed again when the lease expires",
				append(attributes, "error", err)...)
			continue
		}
		logger.Info("send job processed", append(attributes, "outcome", result.Outcome)...)
	}
}

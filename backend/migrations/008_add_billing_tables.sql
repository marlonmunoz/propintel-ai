-- ============================================================================
-- PropIntel AI — Billing tables (Stripe subscription state)
-- Run via: python -m backend.scripts.run_migrations
-- Or paste into Supabase SQL Editor.
-- ============================================================================

CREATE TABLE IF NOT EXISTS billing_customers (
  user_id                TEXT PRIMARY KEY,
  stripe_customer_id     TEXT NOT NULL UNIQUE,
  stripe_subscription_id TEXT,
  subscription_status    TEXT,
  price_id               TEXT,
  current_period_end     TIMESTAMPTZ,
  cancel_at_period_end   BOOLEAN NOT NULL DEFAULT FALSE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_billing_customers_stripe_customer_id
  ON billing_customers (stripe_customer_id);

CREATE INDEX IF NOT EXISTS idx_billing_customers_stripe_subscription_id
  ON billing_customers (stripe_subscription_id);

CREATE TABLE IF NOT EXISTS billing_events (
  id               SERIAL PRIMARY KEY,
  stripe_event_id  TEXT NOT NULL UNIQUE,
  event_type       TEXT NOT NULL,
  user_id          TEXT,
  payload_summary  JSONB,
  received_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_billing_events_user_id
  ON billing_events (user_id);

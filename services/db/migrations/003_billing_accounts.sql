CREATE TABLE IF NOT EXISTS billing_accounts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  stripe_customer_id text,
  stripe_subscription_id text,
  stripe_price_id text,
  status text NOT NULL DEFAULT 'inactive',
  current_period_end timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id),
  UNIQUE (stripe_customer_id),
  UNIQUE (stripe_subscription_id)
);

CREATE INDEX IF NOT EXISTS idx_billing_accounts_org_id ON billing_accounts(org_id);

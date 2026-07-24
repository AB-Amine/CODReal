-- Migration 003: Market anomalies table and security

CREATE TABLE IF NOT EXISTS public.market_anomalies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
    anomaly_type TEXT NOT NULL, -- e.g., 'cpm_spike', 'funnel_drop', 'hour_zero_alert'
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    message TEXT NOT NULL,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.market_anomalies ENABLE ROW LEVEL SECURITY;

-- Select policy: users can only read anomalies linked to their campaigns
CREATE POLICY "Allow users to read anomalies of their campaigns"
    ON public.market_anomalies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.campaigns c
            WHERE c.id = market_anomalies.campaign_id
            AND c.user_id = auth.uid()
        )
    );

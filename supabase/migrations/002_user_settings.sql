-- Migration 002: User threshold settings

CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    return_fee_mad NUMERIC(10,2) DEFAULT 25.00,
    critical_return_rate NUMERIC(4,2) DEFAULT 0.30,
    target_roas NUMERIC(6,2) DEFAULT 2.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

-- Select policy
CREATE POLICY "Allow users to read their own settings"
    ON public.user_settings FOR SELECT
    USING (auth.uid() = user_id);

-- Insert/Update/Delete policy
CREATE POLICY "Allow users to modify their own settings"
    ON public.user_settings FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

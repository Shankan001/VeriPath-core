-- Weather risk events table (corrected to match real farm_boundaries schema)
CREATE TABLE IF NOT EXISTS weather_risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farm_id UUID NOT NULL REFERENCES farm_boundaries(id) ON DELETE CASCADE,
    risk_type TEXT NOT NULL CHECK (risk_type IN ('extreme_heat','flash_flood','unseasonal_rainfall')),
    severity TEXT DEFAULT 'watch' CHECK (severity IN ('watch','warning')),
    forecast_value NUMERIC(6,2),
    forecast_window_hours INT DEFAULT 48,
    recommended_action TEXT,
    sms_sent BOOLEAN DEFAULT FALSE,
    raw_response JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_weather_farm_created ON weather_risk_events (farm_id, created_at DESC);

ALTER TABLE weather_risk_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_all_weather_events ON weather_risk_events
    FOR ALL USING (auth.role() = 'service_role');

-- Dedicated column for audit failure reasons (avoids clobbering the existing
-- 'notes' field, which already stores real KRA PIN / FOB value data)
ALTER TABLE ledger ADD COLUMN IF NOT EXISTS audit_failure_reason TEXT;

-- Company contacts table — field agents and record keepers, for the
-- Quarantine Desk's "Ping Contact via WhatsApp" feature
CREATE TABLE IF NOT EXISTS company_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    contact_type TEXT NOT NULL CHECK (contact_type IN ('field_agent', 'record_keeper')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_company_contacts_company ON company_contacts (company);

ALTER TABLE company_contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_all_company_contacts ON company_contacts
    FOR ALL USING (auth.role() = 'service_role');

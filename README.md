# VeriPath Core

VeriPath is open-source agricultural traceability and compliance software for East African producers and exporters. It helps exporters document where their produce came from and reduce manual paperwork, and it helps livestock owners, including those living abroad, monitor animal health and records.

## Modules

### VeriPath Crops
- Farm registration with geolocation and plot boundaries
- Packhouse intake and daily batch reports
- Pre-audit checks and EUDR deforestation-risk scoring
- Compliance document generation (PDF) and a certificate vault
- Consignment ledger with filtering and export
- Satellite crop-health (NDVI) and weather-risk monitoring
- Role-based access for exporters, compliance officers, record keepers, agronomists and farmers

### VeriPath Livestock
- Animal registry with unique tags, breed, sex and age
- Temperature monitoring with species-specific thresholds
- Symptom logging and disease-risk indicators
- Veterinarian and owner dashboards
- Cost of production, milk, growth and feed tracking, and farm P&L
- Optional public website listings for farms that advertise stock

## Tech stack
Python, Streamlit, PostgreSQL (Supabase), Playwright, ReportLab, Pillow, and the Anthropic API for document parsing.

## Getting started

```bash
git clone https://github.com/Shankan001/VeriPath-core.git
cd VeriPath-core
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your own values
streamlit run app.py
```

VeriPath needs a Supabase (PostgreSQL) project and your own API keys. Incremental SQL migrations are in `supabase_migrations/`. A complete base schema file is planned. Never commit `.env`.

## Project layout
- `app.py`: entry point and navigation
- `livestock_*.py`, `packhouse.py`, `eudr*.py` and others: feature modules
- `supabase_migrations/`: database migrations
- `tools/`: maintenance and verification scripts

## Roadmap
- Physical sensors for packhouse and animal-level verification
- Additional regional portal integrations
- Immutable audit trail for verified lots

## Contributing
Issues and pull requests are welcome. Please do not include credentials or real personal data in any contribution.

## License
Apache License 2.0. See [LICENSE](LICENSE).

© 2026 VeriPath Africa Ltd.

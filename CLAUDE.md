# Barometer — Synapsun PV Price Index

## Project Purpose

Automated pipeline that scrapes weekly solar PV price data from TaiyangNews, extracts prices from images using Claude Vision, stores them in Google Sheets, and displays them in an interactive web dashboard. Used by Synapsun to track polysilicon, wafer, cell, module, and glass prices across the PV supply chain.

## Architecture Overview

```
TaiyangNews website
       ↓  (HTTP scrape, weekly)
taiyangnews_pv_scraper.py
       ↓  (Claude Vision API — image → structured JSON)
Google Sheets (SHEET_ID below)
       ↓  (CSV export, public URL)
index.html / barometre-synapsun.html  (Chart.js dashboards)
```

CI/CD: GitHub Actions runs the scraper every Monday at 08:00 UTC (`pv_price_weekly.yml`).

## Tech Stack

- **Python 3.11** — all backend scripts
- **Claude API** (`anthropic>=0.25.0`) — Vision model for price extraction from images
- **Google Sheets** via `gspread>=6.0.0` + `google-auth>=2.0.0` — data store
- **requests + BeautifulSoup4** — HTML scraping
- **Chart.js** (CDN) — frontend visualizations in the dashboards
- **GitHub Actions** — scheduled automation

## Key Files

| File | Role |
|------|------|
| `taiyangnews_pv_scraper.py` | Primary entry point — weekly scrape, Vision extraction, Sheets upsert |
| `backfill.py` | Full historical backfill + maintenance (manual or scheduled) |
| `index.html` | Main interactive dashboard (loads data from Sheets CSV) |
| `barometre-synapsun.html` | SEO-optimised alternate dashboard |
| `pv_price_weekly.yml` | GitHub Actions workflow (cron + manual dispatch) |
| `requirements.txt` | Python dependencies |

### Maintenance / one-off scripts

| Script | Purpose |
|--------|---------|
| `add_category_column.py` | One-time: insert Category column |
| `clean_units.py` | Strip residual unit strings from price cells |
| `diagnose_products.py` | Find truncated/mismatched product names |
| `fix_missing_weeks.py` | Re-extract empty week columns |
| `fix_numeric_rows.py` | Remove JSON artifact rows |
| `fix_product_names.py` | Bulk rename products from hardcoded list |
| `remove_blocked_rows.py` | Remove blocklisted product rows |

## Critical Constants (taiyangnews_pv_scraper.py)

```python
SHEET_ID = "1uZeF8NfStd_j7_rBL9pmAcT-RrOM4xQ7PE--Siekidw"
SHEET_TAB = "taiyangnews_scrapping"
VALID_CATEGORIES = {"Polysilicon", "Wafer", "Cell", "Module", "Glass", "Unknown"}
SIMILARITY_THRESHOLD = 0.82   # difflib fuzzy-match threshold for product name normalization
```

## Google Sheets Layout

```
Row 1: Category | Product | Show in Barometer | W1-2024 | W2-2024 | ...
Row 2: (blank)  | (blank)  | (blank)           | URL     | URL     | ...
Row 3+: product data rows
```

- Column 1: category, Column 2: canonical product name, Column 3: barometer visibility flag
- Week columns start at index 3 (0-based), header format `W{n}-{yyyy}`

## Required Credentials (environment variables / GitHub Secrets)

| Variable | Used for |
|----------|---------|
| `GOOGLE_CREDENTIALS_JSON` | Google service account JSON (Sheets write access) |
| `ANTHROPIC_API_KEY` | Claude Vision API calls |

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run weekly scraper manually
python taiyangnews_pv_scraper.py

# Full historical backfill
python backfill.py

# One-off maintenance examples
python clean_units.py
python diagnose_products.py
python fix_missing_weeks.py
```

## Conventions & Patterns

- **Language of comments/docstrings:** French
- **Naming:** `snake_case` functions/variables, `UPPER_CASE` constants
- **Claude model used:** `claude-opus-4-5` for Vision tasks
- **Image pipeline:** page HTML → `<img>` URLs → base64 encode → multimodal Claude message → JSON price extraction
- **Product normalisation:** `difflib.SequenceMatcher` at 82% threshold, with an explicit alias map for known variants (e.g. Solar Glass 3.2 mm / 2.0 mm → canonical name)
- **Week fallback:** if the current week's page isn't published yet, the scraper automatically retries the previous week
- **Module start date:** Module category tracked separately from W38-2024 onwards

## Business Rules

- **Blocklist:** 16 product variants are excluded (China Project, HJT variants, etc.) — defined in `BLOCKED_PRODUCTS` inside the scraper
- **KPI label:** "Granular Silicon" is displayed as "FBR Granular Silicon"
- **URL format change:** TaiyangNews changed URL scheme between 2024–2025 and 2026+; the scraper handles both patterns

## Dashboard Data Flow

Both HTML dashboards fetch data via Google Sheets public CSV export:

```
https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_TAB}
```

The dashboards parse this CSV client-side (no server required) and render Chart.js line charts with per-category filtering, KPI cards showing latest prices and week-over-week % change, and date range controls.

## No Test Suite

There are no automated tests. Validation is done through:
1. Google Sheets data inspection after each run
2. Manual execution of diagnostic scripts
3. GitHub Actions run logs

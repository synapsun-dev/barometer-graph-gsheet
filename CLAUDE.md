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

## Nightly Runner — Traitement automatique

Ce projet est traité chaque nuit par `nightly_runner.py`. Modèle et timeout sont sélectionnés automatiquement selon la complexité estimée par le pré-vol (haiku) :

| Tâche | Modèle | Timeout |
|---|---|---|
| Simple (1 fichier, 1 bug, 1 feature) | `claude-sonnet-4-6` | 600–900s |
| Complexe (multi-fichiers, exploration) | `claude-opus-4-8` | 1800s |
| I/O lourd (rotation, migration, ≥50 Mo) | adaptatif | 2700s |
| Sous-tâche atomique | `claude-sonnet-4-6` | ≤900s |

## Rendu documentaire — règle universelle

Quand l'utilisateur demande d'**étudier, analyser ou produire un document** (rapport, analyse, étude, synthèse, plan, fiche, comparatif…) :

1. **Fichier `.md`** — toujours généré (usage interne / Obsidian).
2. **Fichier Word `.docx` ET/OU HTML** — généré systématiquement en plus du `.md`.
   - `.docx` : utiliser `pandoc input.md -o output.docx` ou `python-docx`.
   - `.html` : fichier HTML autonome avec styles inline.
3. **Lien direct** — communiquer le chemin absolu `file:///C:/...` vers chaque fichier produit.

## Pièges opérationnels connus

### Renommage de repo GitHub → workflows désactivés
**Comportement GitHub :** quand un repo est renommé, GitHub désactive automatiquement les workflows `schedule`. Les crons ne tournent plus silencieusement et aucune alerte n'est émise.

**Symptôme :** le sheet cesse de se mettre à jour sans erreur visible ; le health_check est aussi désactivé donc aucun email.

**Procédure de récupération obligatoire après tout renommage :**
1. `gh workflow enable pv_price_weekly.yml`
2. `gh workflow enable health_check.yml`
3. Déclencher manuellement le scraper pour la semaine manquante : `gh workflow run pv_price_weekly.yml --field week=N --field year=YYYY`

**Correctif en place (juin 2026) :** le scraper exit(1) si "Nothing to update" mais lag > 2 semaines → l'email GitHub part même si le health_check est muet. Ce correctif ne couvre que les runs qui tournent ; si les workflows sont désactivés, il faut la procédure manuelle ci-dessus.

---

## No Test Suite

There are no automated tests. Validation is done through:
1. Google Sheets data inspection after each run
2. Manual execution of diagnostic scripts
3. GitHub Actions run logs

## Livrable Feedback — Zone interactive dans les livrables HTML

À partir du 2026-06-17, les livrables HTML majeurs intègrent une **zone de feedback utilisateur**.

Voir `C:\Claude\Dashboard_Pilotage\FEEDBACK_PROTOCOL.md` pour la spécification technique et l'intégration.

---

## Consignation des tâches futures — règle Dashboard de pilotage

Toute chose « à faire plus tard », « à ne pas oublier », ou décision en attente
DOIT être consignée dans un format exploitable par le Dashboard de pilotage —
JAMAIS uniquement dans un fichier de documentation ou de notes (docs/*.md,
README, rapport…) qui sortira des radars.

1. **Tâche future / chantier différé** → entrée `### Tâche N — <titre>` dans la
   section `## Plan d'action détaillé` du `PROJECT.md` (préfixer « EN ATTENTE
   de … » si elle dépend d'une décision ou d'un événement).
2. **Prochaine action immédiate** → frontmatter `prochaine_action` (1 ligne,
   ≤ 300 caractères, sans markdown).
3. **Question à trancher par Franck** → section `## QUESTIONS BLOQUANTES` du
   corps du PROJECT.md.
4. Le détail technique peut rester dans `docs/`, mais le **pointeur** (la tâche)
   doit exister dans le PROJECT.md — c'est lui que le dashboard parse.

Après mise à jour : `python C:/Claude/Dashboard_Pilotage/scripts/aggregate.py`.

"""
TaiyangNews PV Price Index — Scraper principal
-----------------------------------------------
Structure Google Sheet :
  Ligne 1 : Category | Product | Show in Barometer | W1-2024 | W2-2024 | ...
  Ligne 2 : (vide)   | (vide)  | (vide)            | URL_W1  | URL_W2  | ...
  Ligne 3+: données produits

Fonctionnalités :
  - Extraction libre Claude Vision + normalisation difflib (zéro token supplémentaire)
  - Fusion automatique doublons Solar Glass
  - Colonne Show in Barometer : YES par défaut, jamais écrasée
  - URL TaiyangNews écrite automatiquement en ligne 2
  - Liste de blocage permanente pour produits parasites
  - Fallback semaine précédente si page non publiée

Format URL : 2024/2025 → {year}-cw{week} | 2026+ → cw{week}-{year}
"""

import argparse
import base64
import difflib
import json
import logging
import os
import re
import sys
import time
from datetime import date

import anthropic
import gspread
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

# ── LOGGING ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────

SHEET_ID   = "1uZeF8NfStd_j7_rBL9pmAcT-RrOM4xQ7PE--Siekidw"
SHEET_TAB  = "taiyangnews_scrapping"
CLAUDE_MODEL = "claude-opus-4-8"
MIN_EXPECTED_PRODUCTS = 10
MAX_WEEK_LAG = 2  # semaines de retard tolérées avant alerte

# auth/drive removed — scraper only needs write access to one spreadsheet
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SIMILARITY_THRESHOLD = 0.82

VALID_CATEGORIES = {"Polysilicon", "Wafer", "Cell", "Module", "Glass", "Unknown"}

# Loose sanity bounds per category (catches 10× Vision errors, not tight market ranges)
PRICE_BOUNDS = {
    "Polysilicon": (5.0,  500.0),
    "Wafer":       (0.1,  100.0),
    "Cell":        (0.05,  10.0),
    "Module":      (0.05,  10.0),
    "Glass":       (1.0,  500.0),
}

PRODUCT_ALIASES = {
    "3.2mm (rmb/m2)":              "Solar Glass 3.2 mm (RMB/m2)",
    "2.0mm (rmb/m2)":              "Solar Glass 2.0mm (RMB/m2)",
    "solar glass 3.2mm (rmb/m2)":  "Solar Glass 3.2 mm (RMB/m2)",
    "solar glass 2.0 mm (rmb/m2)": "Solar Glass 2.0mm (RMB/m2)",
}

BLOCKED_PRODUCTS = {
    "china project",
    "chinese 5n",
    "n-type 183.75mm",
    "perc bifacial p-type 210mm 66 cells",
    "z-glass",
    "n-type 210mm 150µm wafer",
    "topcon bifacial n-type 210mm 66 cells",
    "210mm hjt module (g15.67mw)",
    "hjt module (g15",
    "german tg-si",
    "global polyqtg",
    "p-type 210mm 130µm wafer",
    "perc bifacial n-type 182mm cell",
    "perc bifacial n-type 210mm cell",
    "210mm hjt module m10",
    "hjt module m10",
    "5-6 piat",
    "(new) (rmb",
}

# Module-level client — created once, reused across all calls
_anthropic_client = anthropic.Anthropic()


# ── HELPERS ───────────────────────────────────────────────────────────────────

def is_blocked(name: str) -> bool:
    n = name.lower()
    return any(p in n for p in BLOCKED_PRODUCTS)


def normalize_alias(name: str) -> str:
    return PRODUCT_ALIASES.get(name.lower(), name)


def validate_price(name: str, category: str, value) -> None:
    """Logs a warning if value is outside expected bounds for its category."""
    if value is None:
        return
    try:
        v = float(value)
    except (ValueError, TypeError):
        logger.warning("Non-numeric price for '%s': %r", name, value)
        return
    bounds = PRICE_BOUNDS.get(category)
    if bounds and not (bounds[0] <= v <= bounds[1]):
        logger.warning(
            "Price out of range for '%s' (%s): %s — expected %.1f–%.1f",
            name, category, v, bounds[0], bounds[1],
        )


# ── URL HELPERS ───────────────────────────────────────────────────────────────

def build_url_candidates(week: int, year: int) -> list:
    """Retourne les URLs candidates à essayer dans l'ordre (TaiyangNews change parfois le format)."""
    base = "https://taiyangnews.info/price-index/taiyangnews-pv-price-index"
    if year >= 2026:
        return [
            f"{base}-cw{week}-{year}",
            f"{base}-cw-{week}-{year}",
        ]
    return [f"{base}-{year}-cw{week}"]


def build_url(week: int, year: int) -> str:
    return build_url_candidates(week, year)[0]


def col_header(week: int, year: int) -> str:
    return f"W{week}-{year}"


def prev_week(week: int, year: int) -> tuple:
    if week == 1:
        py = year - 1
        return date(py, 12, 28).isocalendar()[1], py
    return week - 1, year


def current_week_year() -> tuple:
    today = date.today()
    iso = today.isocalendar()
    return iso[1], iso[0]


def col_index_to_letter(index: int) -> str:
    """Convert 1-based column index to A1-notation letter (e.g. 27 → AA)."""
    if index < 1:
        raise ValueError(f"Column index must be >= 1, got {index}")
    result = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


# ── FETCH & PARSE ─────────────────────────────────────────────────────────────

def _get(url: str):
    """GET avec 3 tentatives. Retourne (resp, url) ou (None, None)."""
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 404:
                return None, None
            resp.raise_for_status()
            return resp, url
        except requests.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status < 500:
                logger.error("HTTP %s — not retrying", status)
                return None, None
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                logger.error("HTTP error after 3 attempts: %s", e)
                return None, None
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                logger.error("Request failed after 3 attempts: %s", e)
                return None, None
    return None, None


def discover_url_from_index(week: int, year: int):
    """
    Scrape la page index TaiyangNews pour trouver l'URL exacte d'une semaine.
    Utilisé comme fallback si les formats connus échouent.
    Retourne l'URL ou None.
    """
    index_url = "https://taiyangnews.info/price-index"
    logger.info("Discovering URL from index page for W%d-%d...", week, year)
    resp, _ = _get(index_url)
    if not resp:
        return None

    # Extrait tous les slugs pv-price-index du HTML
    slugs = re.findall(r'pv-price-index[^"\'> &]+', resp.text, re.IGNORECASE)

    for slug in slugs:
        slug = slug.rstrip("/.,;)")
        # Format 2026+ : cw-20-2026 ou cw20-2026
        m = re.search(r'cw-?(\d+)-(\d{4})$', slug, re.IGNORECASE)
        if m and int(m.group(1)) == week and int(m.group(2)) == year:
            url = f"https://taiyangnews.info/price-index/taiyangnews-{slug}"
            logger.info("Found URL via index: %s", url)
            return url
        # Format 2024/2025 : 2025-cw22
        m = re.search(r'(\d{4})-cw(\d+)$', slug, re.IGNORECASE)
        if m and int(m.group(2)) == week and int(m.group(1)) == year:
            url = f"https://taiyangnews.info/price-index/taiyangnews-{slug}"
            logger.info("Found URL via index: %s", url)
            return url

    logger.info("W%d-%d not found in index page", week, year)
    return None


def fetch_page(week: int, year: int):
    """
    Essaie les formats d'URL connus puis l'index TaiyangNews en fallback.
    Retourne (html, url) ou (None, None).
    """
    for url in build_url_candidates(week, year):
        logger.info("Fetching %s", url)
        resp, actual_url = _get(url)
        if resp:
            return resp.text, actual_url

    # Fallback : découverte via la page index
    discovered = discover_url_from_index(week, year)
    if discovered:
        resp, actual_url = _get(discovered)
        if resp:
            return resp.text, actual_url

    logger.info("404 — page not yet published")
    return None, None


def extract_image_urls(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            u = img.get(attr, "")
            if "media.assettype.com/taiyangnews" in u:
                found.add(u)
    pattern = r'https://media\.assettype\.com/taiyangnews[^"\'> \\]+\.(?:png|jpg|jpeg)'
    for u in re.findall(pattern, html):
        found.add(u)
    clean = {}
    for u in found:
        if u.startswith("//"):
            u = "https:" + u
        base = u.split("?")[0]
        if base not in clean:
            clean[base] = u
    return [u for u in clean.values()
            if "ogImage=true" not in u
            and "favicon" not in u.lower()
            and "logo" not in u.lower()]


def image_to_base64(url: str) -> tuple:
    if url.startswith("//"):
        url = "https:" + url
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
            return base64.standard_b64encode(resp.content).decode("utf-8"), ct
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise


# ── EXTRACTION VISION ─────────────────────────────────────────────────────────

def extract_prices(image_urls: list) -> dict:
    """
    Claude Vision extrait produits, catégories et valeurs.
    Retourne {nom_produit: {"category": str, "value": str|None}}.
    """
    content = []
    for url in image_urls:
        logger.info("  Loading image: %s", url.split("/")[-1][:60])
        b64, mt = image_to_base64(url)
        content.append({"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}})

    content.append({
        "type": "text",
        "text": (
            "Tableau de prix PV. Extrais TOUS les produits avec leur catégorie et prix.\n"
            "Catégories possibles (lignes séparatrices) : Polysilicon, Wafer, Cell, Module, Glass.\n\n"
            "RÈGLES :\n"
            "- Valeur = nombre pur UNIQUEMENT (ex: 38.5, jamais '38.5 RMB/kg')\n"
            "- Produit avec tiret (-) → value = null\n"
            "- Inclure l'unité dans le NOM entre parenthèses\n"
            "- Exclure les lignes séparatrices de catégorie\n"
            "- Exclure les produits 'China Project'\n\n"
            "Format JSON :\n"
            "{\n"
            "  \"N-Type Silicon in China (RMB/kg)\": {\"category\": \"Polysilicon\", \"value\": \"36.0\"},\n"
            "  \"p-type, 182mm, 150µm (RMB/piece)\": {\"category\": \"Wafer\", \"value\": null},\n"
            "  \"TOPCon - n-type 182mm (RMB/W)\": {\"category\": \"Cell\", \"value\": \"0.33\"},\n"
            "  \"Solar Glass 3.2 mm (RMB/m2)\": {\"category\": \"Glass\", \"value\": \"18.5\"}\n"
            "}\n\nJSON uniquement, sans texte autour."
        )
    })

    logger.info("Calling Claude Vision (%s)...", CLAUDE_MODEL)
    msg = None
    for attempt in range(3):
        try:
            msg = _anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                messages=[{"role": "user", "content": content}]
            )
            break
        except anthropic.APIError as e:
            if attempt < 2:
                wait = 2 ** (attempt + 2)
                logger.warning("Claude API error (attempt %d/3): %s — retrying in %ds", attempt + 1, e, wait)
                time.sleep(wait)
            else:
                logger.error("Claude API failed after 3 attempts: %s", e)
                return {}

    if msg is None:
        return {}

    raw = msg.content[0].text.strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON from Claude: %s", e)
        return {}

    # Handle list response format
    if isinstance(data, list):
        converted = {}
        for item in data:
            if isinstance(item, dict):
                name = item.get("product") or item.get("name") or item.get("Product")
                val  = item.get("price") or item.get("value")
                cat  = item.get("category", "Unknown")
                if name and isinstance(name, str) and len(name) > 3:
                    converted[name] = {"category": cat, "value": val}
        data = converted

    if not isinstance(data, dict):
        return {}

    result = {}
    for k, v in data.items():
        if is_blocked(k):
            continue
        k = normalize_alias(k)
        if isinstance(v, dict):
            cat = v.get("category", "Unknown")
            if cat not in VALID_CATEGORIES:
                cat = "Unknown"
            raw_val = v.get("value")
        else:
            cat = "Unknown"
            raw_val = v

        if raw_val is None or str(raw_val).strip() in ("null", "-", ""):
            clean_val = None
        else:
            m = re.search(r'(?:[0-9]+[.,]?[0-9]*|[.,][0-9]+)', str(raw_val))
            clean_val = m.group(0).replace(",", ".") if m else None

        validate_price(k, cat, clean_val)
        result[k] = {"category": cat, "value": clean_val}

    logger.info("Extracted %d product(s)", len(result))
    if len(result) < MIN_EXPECTED_PRODUCTS:
        logger.warning(
            "Only %d products extracted — expected >= %d. Page structure may have changed.",
            len(result), MIN_EXPECTED_PRODUCTS,
        )
    return result


# ── NORMALISATION DIFFLIB ─────────────────────────────────────────────────────

def normalize_with_difflib(extracted: dict, canonical: list) -> dict:
    if not canonical:
        return {k: v for k, v in extracted.items() if not is_blocked(k)}

    normalized = {}
    new_products = []

    for name, data in extracted.items():
        if is_blocked(name):
            continue
        name = normalize_alias(name)
        matches = difflib.get_close_matches(
            name.lower(), [c.lower() for c in canonical],
            n=1, cutoff=SIMILARITY_THRESHOLD
        )
        if matches:
            canon = next(c for c in canonical if c.lower() == matches[0])
            normalized[canon] = data
        else:
            normalized[name] = data
            new_products.append(name)

    if new_products:
        logger.info("New product(s) detected: %s", new_products)

    return normalized


# ── GOOGLE SHEET ──────────────────────────────────────────────────────────────

def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON not set.")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)


def get_existing_headers(ws) -> list:
    return ws.row_values(1)


def get_canonical_products(ws) -> list:
    col_b = ws.col_values(2)
    return [p for p in col_b[2:] if p and p.strip()]


def clean_units(ws) -> None:
    """Strip residual unit strings from price cells (e.g. '38.5 RMB/kg' → '38.5')."""
    logger.info("Cleaning residual units...")
    all_values = ws.get_all_values()
    updates = []

    for row_idx, row in enumerate(all_values):
        if row_idx < 2:
            continue
        for col_idx, cell in enumerate(row):
            if col_idx < 3:
                continue
            if not cell or cell.strip() == "":
                continue
            try:
                float(cell.replace(",", "."))
                continue
            except ValueError:
                pass
            m = re.search(r'(?:[0-9]+[.,]?[0-9]*|[.,][0-9]+)', cell)
            if m:
                cleaned = m.group(0).replace(",", ".")
                col_letter = col_index_to_letter(col_idx + 1)
                updates.append({"range": f"{col_letter}{row_idx + 1}", "values": [[cleaned]]})

    if updates:
        batch_size = 100
        for i in range(0, len(updates), batch_size):
            ws.batch_update(updates[i:i + batch_size])
            time.sleep(2)
        logger.info("Cleaned %d value(s)", len(updates))
    else:
        logger.info("No residual units found")


def remove_blocked_rows(ws) -> None:
    """Delete rows whose product name matches the blocklist."""
    logger.info("Removing blocked rows...")
    col_b = ws.col_values(2)
    to_delete = []
    for i, name in enumerate(col_b):
        if i < 2:
            continue
        if name and is_blocked(name):
            to_delete.append(i + 1)
            logger.info("  Deleting row %d: '%s'", i + 1, name)

    for row_idx in sorted(to_delete, reverse=True):
        ws.delete_rows(row_idx)
        time.sleep(0.3)

    if to_delete:
        logger.info("Deleted %d row(s)", len(to_delete))
    else:
        logger.info("No blocked rows found")


def upsert_week(ws, prices: dict, header: str, page_url: str, force: bool = False):
    """
    Adds or updates a week column.

    Normal mode  : skips if header already exists.
    Force mode   : overwrites existing column prices without touching product
                   rows or the Show-in-Barometer column. Does NOT add new
                   products in force mode (structure must be clean first).

    All writes use batch_update so a crash cannot leave a partial column.
    """
    all_values = ws.get_all_values()

    is_empty = (
        not all_values
        or all_values == [[]]
        or all(all(c == "" for c in row) for row in all_values)
    )

    if is_empty:
        logger.info("Sheet is empty — initialising")
        rows = [["Category", "Product", "Show in Barometer", header]]
        rows.append(["", "", "", page_url])
        for product, data in prices.items():
            rows.append([
                data.get("category", "Unknown"),
                product,
                "YES",
                data.get("value") or ""
            ])
        ws.update(values=rows, range_name="A1")
        return list(prices.keys())

    headers = all_values[0]
    existing_products = [row[1] for row in all_values[2:] if len(row) > 1 and row[1]]

    if header in headers:
        if not force:
            logger.warning("'%s' already present — skipping.", header)
            return existing_products

        # Force mode: overwrite existing column, no structural changes
        col_idx = headers.index(header) + 1
        col_letter = col_index_to_letter(col_idx)
        logger.info("Force-updating '%s' at column %s", header, col_letter)
        price_values = [[prices.get(p, {}).get("value") or ""] for p in existing_products]
        ws.batch_update([
            {"range": f"{col_letter}2", "values": [[page_url]]},
            {"range": f"{col_letter}3", "values": price_values},
        ])
        logger.info("Force-updated %d row(s)", len(price_values))
        return existing_products

    # Normal mode: add new column
    new_products = [p for p in prices.keys() if p not in existing_products]

    if new_products:
        logger.info("Adding %d new product(s)", len(new_products))
        next_row = len(all_values) + 1
        ws.update(
            values=[[prices[p].get("category", "Unknown"), p, "YES"] for p in new_products],
            range_name=f"A{next_row}"
        )
        existing_products = existing_products + new_products

    # Strip trailing empty headers before computing next column index.
    # get_all_values() pads rows to equal width, which can produce hundreds of
    # phantom empty columns that would push new weeks far to the right.
    last_real_col = len([h for h in headers if h.strip()])
    new_col_idx = last_real_col + 1
    col_letter = col_index_to_letter(new_col_idx)
    logger.info("Writing column '%s' at %s", header, col_letter)

    price_values = [[prices.get(p, {}).get("value") or ""] for p in existing_products]

    # Single batch call: header + URL + data are written atomically
    ws.batch_update([
        {"range": f"{col_letter}1", "values": [[header]]},
        {"range": f"{col_letter}2", "values": [[page_url]]},
        {"range": f"{col_letter}3", "values": price_values},
    ])

    logger.info("Wrote %d row(s)", len(price_values))
    return existing_products


# ── LOGIQUE HEBDOMADAIRE ──────────────────────────────────────────────────────

def resolve_week(week: int, year: int, existing_headers: list):
    hdr = col_header(week, year)
    if hdr in existing_headers:
        return None

    html, url = fetch_page(week, year)
    if html:
        return week, year, html, url

    pw, py = prev_week(week, year)
    phdr = col_header(pw, py)
    if phdr in existing_headers:
        # Fallback déjà présent — semaine cible pas encore publiée sur TaiyangNews.
        logger.info(
            "W%d-%d pas encore disponible sur TaiyangNews ; "
            "W%d-%d déjà dans le sheet — sera récupérée au prochain run.",
            week, year, pw, py,
        )
        return None

    html, url = fetch_page(pw, py)
    if html:
        logger.warning(
            "W%d-%d not published yet — falling back to W%d-%d. "
            "Verify TaiyangNews published on schedule.",
            week, year, pw, py,
        )
        return pw, py, html, url

    # Ni la semaine courante ni la précédente ne sont récupérables alors que
    # le Sheet ne contient aucune des deux : échec réel, pas un simple "rien à faire".
    logger.error(
        "Neither W%d-%d nor W%d-%d could be fetched and the sheet has neither — "
        "TaiyangNews scrape failed (site down or URL scheme changed?).",
        week, year, pw, py,
    )
    sys.exit(1)


def process_week(ws, week, year, html, page_url):
    image_urls = extract_image_urls(html)
    if not image_urls:
        logger.error("No images found on page.")
        sys.exit(1)

    prices_raw = extract_prices(image_urls)
    if not prices_raw:
        logger.error("No prices extracted.")
        sys.exit(1)

    canonical = get_canonical_products(ws)
    prices = normalize_with_difflib(prices_raw, canonical)
    upsert_week(ws, prices, col_header(week, year), page_url)


# ── ALERTES ───────────────────────────────────────────────────────────────────

def _check_lag_alert(target_week: int, target_year: int, existing_headers: list) -> None:
    """
    Exit(1) si la semaine cible n'est pas dans le sheet et que le lag dépasse
    MAX_WEEK_LAG. Permet au workflow GitHub Actions d'échouer et d'envoyer un
    email d'alerte même quand TaiyangNews tarde à publier.
    """
    if col_header(target_week, target_year) in existing_headers:
        return  # Semaine déjà présente — rien d'anormal

    week_cols = []
    for h in existing_headers:
        m = re.match(r"W(\d+)-(\d{4})$", h)
        if m:
            week_cols.append((int(m.group(1)), int(m.group(2))))

    if not week_cols:
        return  # Sheet vide, pas d'alerte

    last_w, last_y = max(week_cols, key=lambda x: (x[1], x[0]))
    lag = (
        date.fromisocalendar(target_year, target_week, 1)
        - date.fromisocalendar(last_y, last_w, 1)
    ).days // 7

    if lag > MAX_WEEK_LAG:
        logger.error(
            "ALERTE LAG : W%d-%d absent du sheet — dernier update W%d-%d "
            "(%d sem. de retard, max toléré %d) — "
            "TaiyangNews en retard de publication ou pipeline en panne.",
            target_week, target_year, last_w, last_y, lag, MAX_WEEK_LAG,
        )
        sys.exit(1)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", type=int)
    parser.add_argument("--year", type=int)
    args = parser.parse_args()

    week, year = (args.week, args.year) if (args.week and args.year) else current_week_year()
    logger.info("TaiyangNews — W%d-%d", week, year)

    ws = get_sheet()
    existing_headers = get_existing_headers(ws)

    result = resolve_week(week, year, existing_headers)
    if not result:
        _check_lag_alert(week, year, existing_headers)
        logger.info("Nothing to update.")
        return

    w, y, html, url = result
    process_week(ws, w, y, html, url)
    logger.info("'%s' added successfully.", col_header(w, y))


if __name__ == "__main__":
    main()

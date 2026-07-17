"""
Export JSON du baromètre — contrat de données versionné
--------------------------------------------------------
Lit l'onglet public `taiyangnews_scrapping` du Google Sheet (export CSV gviz,
aucun secret requis), fige les taux de change (EUR/USD, EUR/CNY) et le prix de
l'argent (XAG) au moment de la génération, puis écrit `data/barometer.json`
à la racine du repo (servi par GitHub Pages).

Ce fichier est LE contrat de données consommé par :
  - les dashboards GitHub Pages (index.html, barometre-synapsun.html) ;
  - à terme, l'import cron du portail synapsun.com (`app:import:barometer`).

Toute rupture de format DOIT incrémenter `schema_version`.

Usage :
    python export_json.py [--out CHEMIN] [--csv FICHIER_LOCAL]

`--csv` permet de tester hors ligne avec un export CSV local.
"""

import argparse
import csv
import io
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────

SCHEMA_VERSION = 1

SHEET_ID  = "1uZeF8NfStd_j7_rBL9pmAcT-RrOM4xQ7PE--Siekidw"
SHEET_TAB = "taiyangnews_scrapping"
CSV_URL   = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
    f"?tqx=out:csv&sheet={SHEET_TAB}"
)

# FX : Frankfurter (données BCE, sans clé) puis open.er-api.com en secours
FX_URLS = [
    "https://api.frankfurter.app/latest?from=EUR&to=USD,CNY",
    "https://open.er-api.com/v6/latest/EUR",
]

# Argent XAG : jsDelivr primaire + Cloudflare Pages fallback (cf. health_check.py)
XAG_URLS = [
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/xag.json",
    "https://latest.currency-api.pages.dev/v1/currencies/xag.json",
]

# Seuil (en %) sous lequel la tendance 4 semaines est considérée stable
TREND_THRESHOLD_PCT = 1.0

TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "barometer.json"

WEEK_RE  = re.compile(r"^W(\d{1,2})-(\d{4})$")
FLOAT_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
UNIT_RE  = re.compile(r"\(([^()]*/[^()]*)\)\s*$")  # dernier groupe (X/Y) du nom


# ── EXTRACTION ────────────────────────────────────────────────────────────────

def fetch_csv() -> str:
    """Récupère l'export CSV public du Sheet."""
    resp = requests.get(CSV_URL, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    if resp.text.lstrip().startswith("<!"):
        raise RuntimeError("Le Sheet renvoie du HTML — n'est plus partagé en lecture publique ?")
    return resp.text


def parse_value(cell: str):
    """Cellule → float ou None (tolère unités résiduelles et virgule décimale)."""
    if not cell or not cell.strip():
        return None
    m = FLOAT_RE.search(cell.strip())
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def parse_unit(name: str) -> str:
    """Extrait l'unité du nom de produit, ex. 'Polysilicon Dense (RMB/kg)' → 'RMB/kg'."""
    m = UNIT_RE.search(name.strip())
    return m.group(1).strip() if m else ""


def parse_sheet(csv_text: str) -> tuple[list[str], list[dict]]:
    """CSV → (semaines, produits). Layout : Category | Product | Show | W{n}-{yyyy}…"""
    rows = list(csv.reader(io.StringIO(csv_text)))
    if len(rows) < 3:
        raise RuntimeError(f"CSV trop court : {len(rows)} ligne(s)")

    header = rows[0]
    weeks = [w.strip() for w in header[3:]]
    # Le Sheet peut avoir des colonnes vides en fin de plage → tronquer la queue
    while weeks and not weeks[-1]:
        weeks.pop()
    bad = [w for w in weeks if not WEEK_RE.match(w)]
    if bad:
        raise RuntimeError(f"Colonnes semaine invalides : {bad[:5]}")

    products = []
    for row in rows[1:]:
        if len(row) < 4:
            continue
        category = row[0].strip()
        name     = row[1].strip()
        show     = row[2].strip().upper()
        # La ligne 2 du Sheet est la ligne des URLs de publication → filtrée ici
        if not category or not name or category.lower() == "url":
            continue
        values = [parse_value(c) for c in row[3:3 + len(weeks)]]
        values += [None] * (len(weeks) - len(values))  # aligner sur les semaines
        products.append({
            "category": category,
            "name": name,
            "unit": parse_unit(name),
            "show_in_barometer": show == "YES",
            "values": values,
        })

    if not products:
        raise RuntimeError("Aucune ligne produit exploitable dans le CSV")
    return weeks, products


# ── ENRICHISSEMENT ────────────────────────────────────────────────────────────

def non_null_points(values: list) -> list[tuple[int, float]]:
    """Liste (index_semaine, valeur) des points renseignés."""
    return [(i, v) for i, v in enumerate(values) if v is not None]


def wow_change_pct(values: list):
    """Variation % entre les deux derniers points renseignés, ou None."""
    pts = non_null_points(values)
    if len(pts) < 2:
        return None
    (_, prev), (_, cur) = pts[-2], pts[-1]
    if prev == 0:
        return None
    return round((cur - prev) / prev * 100, 2)


def trend_4w(values: list):
    """Tendance sur ~4 semaines : 'up' / 'down' / 'stable' / None.

    Compare le dernier point au point renseigné le plus proche situé au moins
    4 semaines avant (seuil TREND_THRESHOLD_PCT pour 'stable').
    """
    pts = non_null_points(values)
    if len(pts) < 2:
        return None
    last_idx, last_val = pts[-1]
    ref = next((v for i, v in reversed(pts[:-1]) if i <= last_idx - 4), None)
    if ref is None or ref == 0:
        return None
    pct = (last_val - ref) / ref * 100
    if pct > TREND_THRESHOLD_PCT:
        return "up"
    if pct < -TREND_THRESHOLD_PCT:
        return "down"
    return "stable"


def latest_point(weeks: list[str], values: list):
    """Dernier point renseigné → {'week': …, 'value': …} ou None."""
    pts = non_null_points(values)
    if not pts:
        return None
    i, v = pts[-1]
    return {"week": weeks[i], "value": v}


def fetch_fx() -> dict:
    """Fige EUR/USD, EUR/CNY et XAG (USD/oz). Champs à None si les APIs échouent."""
    fx = {
        "eur_usd": None,
        "eur_cny": None,
        "xag_usd_oz": None,
        "fixed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    for url in FX_URLS:
        try:
            rates = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json().get("rates", {})
            usd, cny = rates.get("USD"), rates.get("CNY")
            if usd and cny and 0.5 < usd < 2 and 4 < cny < 12:
                fx["eur_usd"], fx["eur_cny"] = round(usd, 4), round(cny, 4)
                break
        except (requests.RequestException, ValueError) as exc:
            logger.warning("FX indisponible via %s : %s", url, exc)
    for url in XAG_URLS:
        try:
            price = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json().get("xag", {}).get("usd")
            if price and 5 < price < 500:
                fx["xag_usd_oz"] = round(price, 2)
                break
        except (requests.RequestException, ValueError) as exc:
            logger.warning("XAG indisponible via %s : %s", url, exc)
    return fx


# ── EXPORT ────────────────────────────────────────────────────────────────────

def build_payload(weeks: list[str], products: list[dict], fx: dict) -> dict:
    last_idx = max((max(i for i, _ in non_null_points(p["values"]))
                    for p in products if non_null_points(p["values"])), default=None)
    if last_idx is None:
        raise RuntimeError("Aucune valeur numérique dans le Sheet")

    for p in products:
        p["latest"] = latest_point(weeks, p["values"])
        p["wow_change_pct"] = wow_change_pct(p["values"])
        p["trend_4w"] = trend_4w(p["values"])

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "TaiyangNews (via Google Sheets Synapsun)",
        "sheet_id": SHEET_ID,
        "last_week": weeks[last_idx],
        "weeks": weeks,
        "fx": fx,
        "market_comment": {"fr": None, "en": None},  # réservé Lot 1 roadmap v2
        "products": products,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporte data/barometer.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Fichier de sortie (défaut : {DEFAULT_OUT})")
    parser.add_argument("--csv", type=Path, default=None,
                        help="CSV local (test hors ligne) au lieu du Sheet")
    args = parser.parse_args()

    csv_text = args.csv.read_text(encoding="utf-8") if args.csv else fetch_csv()
    weeks, products = parse_sheet(csv_text)
    logger.info("Sheet parsé : %d produits, %d semaines", len(products), len(weeks))

    fx = fetch_fx()
    logger.info("FX figés : EUR/USD=%s EUR/CNY=%s XAG=%s USD/oz",
                fx["eur_usd"], fx["eur_cny"], fx["xag_usd_oz"])

    payload = build_payload(weeks, products, fx)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    size_kb = args.out.stat().st_size / 1024
    logger.info("Écrit %s (%.1f Ko) — last_week=%s, %d produits",
                args.out, size_kb, payload["last_week"], len(products))
    return 0


if __name__ == "__main__":
    sys.exit(main())

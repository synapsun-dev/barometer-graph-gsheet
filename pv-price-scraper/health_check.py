"""
Health check quotidien — Baromètre Synapsun
--------------------------------------------
Vérifie que toutes les sources de données et iframes du dashboard répondent :
  1. CSV Google Sheets (disponibilité + fraîcheur des données — dernière semaine)
  2. Dashboard GitHub Pages (it-dev-synapsun.github.io/graph-gsheet-tayang)
  3. Iframes Zoho Analytics (sea freight, etc.)
  4. API BCE (taux de change EUR/USD, EUR/CNY)
  5. API argent XAG (jsDelivr + fallback Cloudflare Pages)
  6. Site TaiyangNews (source du scraping hebdomadaire)

Sort avec un code != 0 si au moins un check échoue → le workflow GitHub Actions
échoue → notification email native GitHub.

Aucun secret requis : toutes les URLs sont publiques.
"""

import logging
import os
import re
import sys
import time
from datetime import date

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────

SHEET_ID  = "1uZeF8NfStd_j7_rBL9pmAcT-RrOM4xQ7PE--Siekidw"
SHEET_TAB = "taiyangnews_scrapping"
CSV_URL   = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
    f"?tqx=out:csv&sheet={SHEET_TAB}"
)

DASHBOARD_URL = "https://it-dev-synapsun.github.io/graph-gsheet-tayang/"

ZOHO_IFRAMES = {
    "Zoho Analytics — Sea freight": (
        "https://analytics.zoho.com/open-view/1373627000027120086/"
        "d6435972ee5651e23d81649703e4b2320b5f037c5a75c8bb38c908c5e858f431"
    ),
    "Zoho Analytics — Vue 2": (
        "https://analytics.zoho.com/open-view/1373627000026674231/"
        "85b92126b565480a6ccb0c28c0eb82a29c5bc7bb3263cdbf8b70430334460571"
    ),
}

ECB_URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
    "?lastNObservations=1&format=csvdata"
)

XAG_URLS = [
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/xag.json",
    "https://latest.currency-api.pages.dev/v1/currencies/xag.json",
]

TAIYANGNEWS_URL = "https://taiyangnews.info/price-index"

# Retard max toléré pour la dernière colonne du Sheet (en semaines ISO).
# Le scraper tourne le lundi ; TaiyangNews publie parfois avec quelques jours
# de retard — au-delà de 2 semaines c'est anormal.
MAX_WEEK_LAG = 2

TIMEOUT     = 30
RETRIES     = 3
RETRY_DELAY = 15  # secondes entre tentatives — évite les fausses alertes transitoires

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def http_get(url: str) -> requests.Response:
    """GET avec retries — lève RuntimeError après RETRIES échecs."""
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200:
                return resp
            last_err = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_err = f"{type(exc).__name__}: {exc}"
        if attempt < RETRIES:
            logger.info("Retry %d/%d for %s (%s)", attempt, RETRIES, url, last_err)
            time.sleep(RETRY_DELAY)
    raise RuntimeError(f"{last_err} — {url}")


def week_lag(latest_week: int, latest_year: int) -> int:
    """Nombre de semaines ISO entre la dernière colonne du Sheet et aujourd'hui."""
    latest = date.fromisocalendar(latest_year, latest_week, 1)
    cur_year, cur_week, _ = date.today().isocalendar()
    current = date.fromisocalendar(cur_year, cur_week, 1)
    return (current - latest).days // 7


# ── CHECKS ────────────────────────────────────────────────────────────────────

def latest_published_on_taiyangnews():
    """Dernière semaine publiée sur la page index TaiyangNews, ou None."""
    try:
        html = http_get(TAIYANGNEWS_URL).text
        found = re.findall(r'cw-?(\d{1,2})-(\d{4})', html)          # format 2026+
        found += [(w, y) for y, w in re.findall(r'(\d{4})-cw(\d{1,2})', html)]
        if not found:
            return None
        return max((int(y), int(w)) for w, y in found)  # (year, week)
    except RuntimeError:
        return None


def check_sheets_csv() -> str:
    resp = http_get(CSV_URL)
    header = resp.text.splitlines()[0] if resp.text else ""
    weeks = re.findall(r'W(\d{1,2})-(\d{4})', header)
    if not weeks:
        raise RuntimeError("CSV accessible mais aucune colonne W{n}-{yyyy} trouvée")
    latest_year, latest_week = max((int(y), int(w)) for w, y in weeks)
    lag = week_lag(latest_week, latest_year)
    if lag > MAX_WEEK_LAG:
        # Distinguer pipeline cassé vs. source en retard
        published = latest_published_on_taiyangnews()
        if published and published > (latest_year, latest_week):
            raise RuntimeError(
                f"PIPELINE EN PANNE : le Sheet s'arrête à W{latest_week}-{latest_year} "
                f"alors que TaiyangNews a publié W{published[1]}-{published[0]} — "
                f"le scraper n'a pas intégré les dernières semaines"
            )
        raise RuntimeError(
            f"SOURCE EN RETARD : TaiyangNews n'a rien publié depuis "
            f"W{latest_week}-{latest_year} ({lag} semaines, max toléré {MAX_WEEK_LAG}) — "
            f"pipeline OK, données indisponibles côté source"
        )
    return f"dernière semaine W{latest_week}-{latest_year} (retard {lag} sem.)"


def check_dashboard() -> str:
    resp = http_get(DASHBOARD_URL)
    if "<canvas" not in resp.text:
        raise RuntimeError("Page chargée mais aucun <canvas> Chart.js trouvé")
    return f"{len(resp.text)} octets, canvas présents"


def make_zoho_check(url: str):
    def check() -> str:
        resp = http_get(url)
        return f"HTTP 200 ({len(resp.text)} octets)"
    return check


def check_ecb() -> str:
    resp = http_get(ECB_URL)
    if not resp.text.strip():
        raise RuntimeError("Réponse BCE vide")
    return "taux EUR/USD disponible"


def check_xag() -> str:
    """OK si au moins une des deux URLs (primaire + fallback) répond correctement."""
    errors = []
    for url in XAG_URLS:
        try:
            resp = http_get(url)
            price = resp.json().get("xag", {}).get("usd")
            if not price or price < 5:
                raise RuntimeError(f"Prix XAG invalide : {price!r}")
            label = "primaire" if url == XAG_URLS[0] else "fallback"
            if errors:
                logger.warning("XAG primaire KO, fallback OK : %s", errors[0])
            return f"{price} USD/oz via {label}"
        except (RuntimeError, ValueError) as exc:
            errors.append(str(exc))
    raise RuntimeError(f"Primaire et fallback KO : {' | '.join(errors)}")


def check_taiyangnews() -> str:
    resp = http_get(TAIYANGNEWS_URL)
    return f"HTTP 200 ({len(resp.text)} octets)"


CHECKS = [
    ("Google Sheets CSV",        check_sheets_csv),
    ("Dashboard GitHub Pages",   check_dashboard),
    ("API BCE (taux de change)", check_ecb),
    ("API XAG (argent)",         check_xag),
    ("TaiyangNews price-index",  check_taiyangnews),
] + [(name, make_zoho_check(url)) for name, url in ZOHO_IFRAMES.items()]


# ── MAIN ──────────────────────────────────────────────────────────────────────

def write_github_summary(results: list):
    """Écrit un tableau markdown dans le résumé du job GitHub Actions."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## Health Check — Baromètre Synapsun",
        "",
        "| Check | Statut | Détail |",
        "|---|---|---|",
    ]
    for name, ok, detail in results:
        icon = "✅" if ok else "❌"
        lines.append(f"| {name} | {icon} | {detail} |")
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    results = []
    for name, check in CHECKS:
        try:
            detail = check()
            logger.info("OK    — %s : %s", name, detail)
            results.append((name, True, detail))
        except Exception as exc:
            logger.error("ÉCHEC — %s : %s", name, exc)
            results.append((name, False, str(exc)))

    write_github_summary(results)

    failures = [r for r in results if not r[1]]
    if failures:
        logger.error("%d/%d check(s) en échec", len(failures), len(results))
        sys.exit(1)
    logger.info("Tous les checks sont OK (%d/%d)", len(results), len(results))


if __name__ == "__main__":
    main()

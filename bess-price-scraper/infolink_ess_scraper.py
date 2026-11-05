"""
InfoLink ESS Spot Price — Scraper hebdomadaire (baromètre batteries / BESS)
---------------------------------------------------------------------------
Source : articles hebdomadaires « ess-spot-price-YYYYMMDD » d'InfoLink Consulting
         https://www.infolink-group.com/energy/energy-storage-supply-chain
         (texte HTML, pas d'image → aucune extraction Vision, aucun appel API Claude)

Structure Google Sheet (même Sheet que le baromètre modules, onglet dédié) :
  Ligne 1 : Category | Product | Show in Barometer | W34-2025 | W36-2025 | ...
  Ligne 2 : (vide)   | (vide)  | (vide)            | URL_W34  | URL_W36  | ...
  Ligne 3+: données produits

Catégories : Lithium (carbonate + spodumène), Cell (LFP ESS 100/280/314 Ah),
             System (conteneurs liquid-cooled DC 2h, AC 1h/2h/4h) — prix Chine.

Fonctionnalités :
  - Découverte automatique des publications (liste « Review » des pages InfoLink)
  - Une colonne par semaine ISO (si deux articles tombent la même semaine, le
    plus récent l'emporte) ; colonnes insérées dans l'ordre chronologique
  - Parsing texte par expressions régulières + bornes de vraisemblance
  - Lignes low/high conservées mais masquées (Show in Barometer = NO)
  - Création de l'onglet s'il n'existe pas
  - exit(1) si le retard dépasse MAX_WEEK_LAG semaines sans nouvelle publication

Usage :
    python infolink_ess_scraper.py                 # semaine courante (+ rattrapage ≤ 3 semaines)
    python infolink_ess_scraper.py --backfill      # toutes les publications manquantes
    python infolink_ess_scraper.py --dry-run       # parse sans écrire dans le Sheet
    python infolink_ess_scraper.py --html page.html --dry-run   # test hors ligne
"""

import argparse
import html as html_lib
import json
import logging
import os
import re
import sys
import time
from datetime import date, datetime

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────

SHEET_ID  = "1uZeF8NfStd_j7_rBL9pmAcT-RrOM4xQ7PE--Siekidw"   # Sheet baromètre modules
SHEET_TAB = "bess_scrapping"
SCOPES    = ["https://www.googleapis.com/auth/spreadsheets"]

INDEX_URL   = "https://www.infolink-group.com/energy/energy-storage-supply-chain"
ARTICLE_URL = "https://www.infolink-group.com/energy-article/ess-spot-price-{ymd}"
SLUG_RE     = re.compile(r"ess-spot-price-(\d{8})")

MAX_WEEK_LAG   = 3      # InfoLink publie chaque mercredi depuis mai 2026 (bimensuel avant)
WEEKLY_CATCHUP = 3      # en mode hebdo, rattrape au plus N semaines manquantes
REQUEST_DELAY  = 1.5    # politesse entre deux pages
TIMEOUT        = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Bornes de vraisemblance (large : attrape une erreur de parsing, pas une
# variation de marché)
PRICE_BOUNDS = {
    "Lithium": {"RMB/MT": (20_000, 600_000), "USD/MT": (200, 8_000)},
    "Cell":    {"RMB/Wh": (0.10, 1.50)},
    "System":  {"RMB/Wh": (0.15, 2.00)},
}

# Noms canoniques (le suffixe d'unité est lu par export_json.py / index.html)
P_LITHIUM   = "Lithium Carbonate battery-grade spot (RMB/MT)"
P_SPODUMENE = "Spodumene Concentrate SC6 CIF (USD/MT)"
P_CELL      = "LFP ESS Cell {ah}Ah (RMB/Wh)"
P_SYSTEM    = "ESS {side}-side liquid-cooled container {h}h (RMB/Wh)"

DASH = r"[–—\-~〜～]"   # – — - ~ 〜 ～
NUM  = r"(\d[\d,]*(?:\.\d+)?)"


# ── HELPERS ───────────────────────────────────────────────────────────────────

def to_float(s: str):
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def col_header(d: date) -> str:
    iso = d.isocalendar()
    return f"W{iso[1]}-{iso[0]}"


def header_key(h: str):
    """'W12-2026' → (2026, 12) pour trier chronologiquement ; None sinon."""
    m = re.match(r"^W(\d{1,2})-(\d{4})$", h.strip())
    return (int(m.group(2)), int(m.group(1))) if m else None


def col_index_to_letter(index: int) -> str:
    result = ""
    while index > 0:
        index, rem = divmod(index - 1, 26)
        result = chr(65 + rem) + result
    return result


def in_bounds(category: str, unit: str, value: float) -> bool:
    lo, hi = PRICE_BOUNDS.get(category, {}).get(unit, (None, None))
    return lo is None or lo <= value <= hi


# ── FETCH ─────────────────────────────────────────────────────────────────────

def _get(url: str):
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                logger.error("Échec GET %s : %s", url, exc)
    return None


def discover_publications() -> list:
    """Retourne les dates (date) de toutes les publications ess-spot-price, triées."""
    found = set()
    page = _get(INDEX_URL)
    if page:
        found.update(SLUG_RE.findall(page))
    if not found:
        # Repli : la page du dernier article connu liste aussi les publications
        page = _get(ARTICLE_URL.format(ymd=date.today().strftime("%Y%m%d")))
        if page:
            found.update(SLUG_RE.findall(page))
    dates = []
    for ymd in found:
        try:
            dates.append(datetime.strptime(ymd, "%Y%m%d").date())
        except ValueError:
            continue
    dates.sort()
    logger.info("%d publication(s) InfoLink découverte(s) (%s → %s)",
                len(dates), dates[0] if dates else "-", dates[-1] if dates else "-")
    return dates


# ── PARSE ─────────────────────────────────────────────────────────────────────

def html_to_text(raw: str) -> str:
    """HTML → texte brut ligne par ligne (sans dépendance externe)."""
    s = re.sub(r"<(script|style|header|footer|nav|form|select)\b.*?</\1>", " ", raw,
               flags=re.S | re.I)
    s = re.sub(r"</(p|div|h\d|li|tr|td|th|br)\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s


def parse_article(raw_html: str) -> dict:
    """
    Extrait les prix d'un article hebdomadaire InfoLink.
    Retour : {nom_produit: {"category": ..., "value": float, "show": "YES"/"NO"}}
    """
    text = html_to_text(raw_html)
    # Ne garder que le corps (avant la liste « Review » qui répète d'autres titres)
    cut = re.search(r"\n\s*(PREV|NEXT|Review|Keywords search)\s*\n", text)
    body = text[:cut.start()] if cut else text
    prices = {}

    def add(name, category, value, show="YES"):
        if value is None:
            return
        unit = re.search(r"\(([^()]+)\)\s*$", name).group(1)
        if not in_bounds(category, unit, value):
            logger.warning("Valeur hors bornes ignorée : %s = %s", name, value)
            return
        prices[name] = {"category": category, "value": value, "show": show}

    # ── Lithium : blocs « Battery-grade lithium carbonate … Average price: RMB 90,000/MT »
    def block_prices(label_re, unit):
        m = re.search(label_re, body, flags=re.I)
        if not m:
            return None, None, None
        seg = body[m.end(): m.end() + 600]
        # Forme 1 (liste) : « Price range: RMB 89,000–91,000/MT » / « Average price: RMB 90,000/MT »
        rng = re.search(rf"Price range:?\s*(?:RMB|USD)?\s*{NUM}\s*{DASH}\s*{NUM}\s*/\s*{unit}", seg, re.I)
        avg = re.search(rf"Average price:?\s*(?:RMB|USD)?\s*{NUM}\s*/\s*{unit}", seg, re.I)
        # Forme 2 (prose) : « … to RMB 180,000–184,000/MT, averaging RMB 182,000/MT »
        if not rng:
            rng = re.search(rf"(?:RMB|USD)\s*{NUM}\s*{DASH}\s*{NUM}\s*/\s*{unit}", seg, re.I)
        if not avg:
            avg = re.search(rf"averag\w*\s*(?:at\s*)?(?:RMB|USD)\s*{NUM}\s*/\s*{unit}", seg, re.I)
        lo, hi = (to_float(rng.group(1)), to_float(rng.group(2))) if rng else (None, None)
        av = to_float(avg.group(1)) if avg else (round((lo + hi) / 2) if lo and hi else None)
        return lo, hi, av

    lo, hi, av = block_prices(r"Battery-grade lithium carbonate", "MT")
    add(P_LITHIUM, "Lithium", av)
    add(P_LITHIUM.replace(" (", " low ("), "Lithium", lo, "NO")
    add(P_LITHIUM.replace(" (", " high ("), "Lithium", hi, "NO")

    lo, hi, av = block_prices(r"Spodumene concentrate\s*\(SC6", "MT")
    add(P_SPODUMENE, "Lithium", av)
    add(P_SPODUMENE.replace(" (", " low ("), "Lithium", lo, "NO")
    add(P_SPODUMENE.replace(" (", " high ("), "Lithium", hi, "NO")

    # ── Cellules : « 314 Ah: RMB 0.325–0.380/Wh, averaging RMB 0.353/Wh »
    for m in re.finditer(
        rf"(\d{{3}})\s*Ah\s*:?\s*RMB\s*{NUM}\s*{DASH}\s*{NUM}\s*/\s*Wh[^\n]*?averag\w*\s*(?:at\s*)?RMB\s*{NUM}\s*/\s*Wh",
        body, flags=re.I,
    ):
        ah = m.group(1)
        name = P_CELL.format(ah=ah)
        add(name, "Cell", to_float(m.group(4)))
        add(name.replace(" (", " low ("), "Cell", to_float(m.group(2)), "NO")
        add(name.replace(" (", " high ("), "Cell", to_float(m.group(3)), "NO")

    # ── Systèmes, deux formes :
    #   « DC-side liquid-cooled containerized ESS (2h): RMB 0.41–0.49/Wh, averaging RMB 0.45/Wh »
    #   « 2-hour DC-side liquid-cooled containerized ESS: RMB 0.44–0.53/Wh, averaging RMB 0.49/Wh »
    sys_patterns = [
        rf"(?P<side>DC|AC)-side[^\n(]*\(\s*(?P<h>\d)\s*h\s*\)\s*:?\s*RMB\s*(?P<lo>{NUM[1:-1]})\s*{DASH}\s*(?P<hi>{NUM[1:-1]})\s*/\s*Wh[^\n]*?averag\w*\s*(?:at\s*)?RMB\s*(?P<av>{NUM[1:-1]})\s*/\s*Wh",
        rf"(?P<h>\d)\s*-?\s*hour\s+(?P<side>DC|AC)-side[^\n:]*:?\s*RMB\s*(?P<lo>{NUM[1:-1]})\s*{DASH}\s*(?P<hi>{NUM[1:-1]})\s*/\s*Wh[^\n]*?averag\w*\s*(?:at\s*)?RMB\s*(?P<av>{NUM[1:-1]})\s*/\s*Wh",
    ]
    for pat in sys_patterns:
        for m in re.finditer(pat, body, flags=re.I):
            name = P_SYSTEM.format(side=m.group("side").upper(), h=m.group("h"))
            if name in prices:
                continue
            add(name, "System", to_float(m.group("av")))
            add(name.replace(" (", " low ("), "System", to_float(m.group("lo")), "NO")
            add(name.replace(" (", " high ("), "System", to_float(m.group("hi")), "NO")

    visible = [n for n, p in prices.items() if p["show"] == "YES"]
    logger.info("Parse : %d série(s) visibles — %s", len(visible), ", ".join(visible))
    return prices


MIN_EXPECTED_VISIBLE = 4   # lithium + ≥ 2 cellules + ≥ 1 système (anciens articles sans systèmes)


# ── GOOGLE SHEET ──────────────────────────────────────────────────────────────

def get_sheet():
    import gspread
    from google.oauth2.service_account import Credentials

    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON non défini.")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(SHEET_ID)
    ensure_aux_tabs(sh)
    try:
        ws = sh.worksheet(SHEET_TAB)
    except gspread.exceptions.WorksheetNotFound:
        logger.info("Onglet '%s' absent — création", SHEET_TAB)
        ws = sh.add_worksheet(title=SHEET_TAB, rows=60, cols=400)
    # Ligne 1 figée : l'export CSV gviz (lu par export_json.py / index.html) prend
    # les lignes figées comme en-tête ; sans cela il fusionne lignes 1 et 2
    # ("W34-2025 https://…") et les colonnes semaine deviennent invalides.
    if ws.frozen_row_count != 1:
        ws.freeze(rows=1)
        logger.info("Ligne 1 figée sur '%s' (en-tête gviz)", SHEET_TAB)
    return ws


def existing_headers(ws) -> list:
    return [h for h in ws.row_values(1) if h.strip()]


# Onglets annexes lus par barometre-bess.html — créés vides (en-têtes seuls)
# s'ils n'existent pas, pour que l'équipe n'ait qu'à les remplir.
AUX_TABS = {
    "Analysis_BESS": [
        ["block_key", "title_fr", "title_en", "title_de", "title_it", "title_es",
         "analysis_fr", "analysis_en", "analysis_de", "analysis_it", "analysis_es",
         "sources", "publish_date", "status"],
        ["bess_lithium"], ["bess_cell"], ["bess_cost_breakdown"], ["bess_system"],
        ["sea_freight"], ["exchange_rate"], ["bess_fca"], ["bess_market_analysis"],
    ],
    "bess_fca_europe": [
        ["date", "ci_eur_kwh", "utility_eur_kwh", "note"],
        ["# date YYYY-MM-DD ou YYYY-MM · prix FCA entrepôt Europe HT hors transport, €/kWh · "
         "C&I = armoire 100-500 kWh · Utility = conteneur ≥ 2 MWh — lignes '#' ignorées", "", "", ""],
    ],
}


def ensure_aux_tabs(sh) -> None:
    import gspread
    for title, rows in AUX_TABS.items():
        try:
            sh.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=50, cols=max(len(r) for r in rows) + 2)
            ws.update(values=rows, range_name="A1")
            logger.info("Onglet annexe '%s' créé (en-têtes)", title)


def upsert_week(ws, prices: dict, header: str, page_url: str, force: bool = False):
    """
    Ajoute (ou réécrit avec force=True) la colonne `header`, insérée à sa place
    chronologique. Les nouveaux produits sont ajoutés en bas (Show = YES/NO
    selon la série). Écritures groupées (batch_update).
    """
    all_values = ws.get_all_values()
    is_empty = not all_values or all(all(c == "" for c in row) for row in all_values)

    if is_empty:
        rows = [["Category", "Product", "Show in Barometer", header], ["", "", "", page_url]]
        for name, p in prices.items():
            rows.append([p["category"], name, p["show"], p["value"]])
        ws.update(values=rows, range_name="A1")
        logger.info("Onglet initialisé avec '%s' (%d lignes)", header, len(rows) - 2)
        return

    headers = [h for h in all_values[0]]
    while headers and not headers[-1].strip():
        headers.pop()
    products = [r[1] for r in all_values[2:] if len(r) > 1 and r[1].strip()]

    # Nouveaux produits → ajout en bas
    new_products = [n for n in prices if n not in products]
    if new_products:
        start_row = 3 + len(products)
        ws.update(
            values=[[prices[n]["category"], n, prices[n]["show"]] for n in new_products],
            range_name=f"A{start_row}",
        )
        products += new_products
        logger.info("%d nouveau(x) produit(s) ajouté(s)", len(new_products))

    if header in headers:
        if not force:
            logger.info("'%s' déjà présent — ignoré", header)
            return
        col = headers.index(header) + 1
    else:
        # Position chronologique : après la dernière colonne de semaine antérieure
        key = header_key(header)
        col = len(headers) + 1
        for i, h in enumerate(headers[3:], start=4):
            k = header_key(h)
            if k and key and k > key:
                col = i
                break
        if col <= len(headers):
            ws.insert_cols([[]], col=col)
            logger.info("Colonne insérée en position %s (ordre chronologique)", col_index_to_letter(col))

    letter = col_index_to_letter(col)
    values = [[prices[n]["value"] if n in prices else ""] for n in products]
    ws.batch_update([
        {"range": f"{letter}1", "values": [[header]]},
        {"range": f"{letter}2", "values": [[page_url]]},
        {"range": f"{letter}3", "values": values},
    ])
    logger.info("'%s' écrit en colonne %s (%d valeurs)", header, letter,
                sum(1 for v in values if v[0] != ""))


# ── ALERTE LAG ────────────────────────────────────────────────────────────────

def check_lag(headers: list) -> None:
    keys = [header_key(h) for h in headers]
    keys = [k for k in keys if k]
    if not keys:
        return
    y, w = max(keys)
    last = date.fromisocalendar(y, w, 3)
    lag = (date.today() - last).days // 7
    if lag > MAX_WEEK_LAG:
        logger.error("ALERTE LAG : dernière semaine W%d-%d, %d semaine(s) de retard (max %d) — "
                     "InfoLink en retard ou pipeline en panne.", w, y, lag, MAX_WEEK_LAG)
        sys.exit(1)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", action="store_true", help="rattrape toutes les publications manquantes")
    ap.add_argument("--force", action="store_true", help="réécrit les colonnes déjà présentes")
    ap.add_argument("--dry-run", action="store_true", help="n'écrit rien dans le Sheet")
    ap.add_argument("--html", help="fichier HTML local (test hors ligne, implique --dry-run)")
    ap.add_argument("--date", help="forcer une publication YYYYMMDD")
    ap.add_argument("--dump-csv", help="(dry-run) écrit le résultat au format CSV de l'onglet "
                                        "(testable avec export_json.py --csv)")
    args = ap.parse_args()
    if args.dump_csv:
        args.dry_run = True

    if args.html:
        raw = open(args.html, encoding="utf-8", errors="ignore").read()
        prices = parse_article(raw)
        print(json.dumps(prices, indent=2, ensure_ascii=False))
        return

    if args.date:
        pubs = [datetime.strptime(args.date, "%Y%m%d").date()]
    else:
        pubs = discover_publications()
        if not pubs:
            logger.error("Aucune publication découverte — site InfoLink injoignable ou structure changée.")
            sys.exit(1)

    # Une publication par semaine ISO (la plus récente)
    by_week = {}
    for d in pubs:
        by_week[col_header(d)] = d
    ordered = sorted(by_week.items(), key=lambda kv: header_key(kv[0]))

    ws = None
    headers = []
    if not args.dry_run:
        ws = get_sheet()
        headers = existing_headers(ws)

    todo = [(h, d) for h, d in ordered if args.force or h not in headers]
    if not args.backfill and not args.force:
        todo = todo[-WEEKLY_CATCHUP:]

    if not todo:
        logger.info("Rien à mettre à jour.")
        check_lag(headers)
        return

    done = 0
    dump = {}   # header → (url, prices) pour --dump-csv
    for header, d in todo:
        url = ARTICLE_URL.format(ymd=d.strftime("%Y%m%d"))
        raw = _get(url)
        if not raw:
            logger.warning("%s introuvable (%s)", header, url)
            continue
        prices = parse_article(raw)
        visible = sum(1 for p in prices.values() if p["show"] == "YES")
        if visible < MIN_EXPECTED_VISIBLE:
            logger.error("%s : seulement %d série(s) visibles — format InfoLink changé ?", header, visible)
            continue
        if args.dry_run:
            logger.info("[dry-run] %s ← %s : %s", header, url,
                        {n: p["value"] for n, p in prices.items() if p["show"] == "YES"})
            dump[header] = (url, prices)
        else:
            upsert_week(ws, prices, header, url, force=args.force)
            headers = existing_headers(ws)
        done += 1
        time.sleep(REQUEST_DELAY)

    if done == 0:
        logger.error("Aucune semaine écrite.")
        sys.exit(1)
    logger.info("%d semaine(s) traitée(s).", done)

    if args.dump_csv and dump:
        import csv
        weeks = list(dump.keys())
        names = []
        for _, pr in dump.values():
            for n in pr:
                if n not in names:
                    names.append(n)
        meta = {n: next(pr[n] for _, pr in dump.values() if n in pr) for n in names}
        with open(args.dump_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Category", "Product", "Show in Barometer"] + weeks)
            w.writerow(["", "", ""] + [dump[h][0] for h in weeks])
            for n in names:
                w.writerow([meta[n]["category"], n, meta[n]["show"]]
                           + [dump[h][1].get(n, {}).get("value", "") for h in weeks])
        logger.info("CSV écrit : %s (%d semaines × %d séries)", args.dump_csv, len(weeks), len(names))
    if not args.dry_run:
        check_lag(headers)


if __name__ == "__main__":
    main()

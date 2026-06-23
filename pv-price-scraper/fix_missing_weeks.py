"""
Relance l'extraction pour les semaines absentes ou avec colonne vide.
"""

import argparse
import time
from datetime import date

from taiyangnews_pv_scraper import (
    col_header, fetch_page, extract_image_urls,
    extract_prices, normalize_with_difflib,
    get_sheet, get_existing_headers, get_canonical_products,
    upsert_week, col_index_to_letter
)


def all_weeks_from(start_week: int, start_year: int):
    today = date.today()
    end_week, end_year = today.isocalendar()[1], today.isocalendar()[0]
    w, y = start_week, start_year
    while (y, w) <= (end_year, end_week):
        yield w, y
        last_week = date(y, 12, 28).isocalendar()[1]
        if w >= last_week:
            w, y = 1, y + 1
        else:
            w += 1


def get_empty_columns(ws, headers: list) -> set:
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return set()
    empty = set()
    # Données commencent en colonne D (index 3) car A=Category, B=Product, C=Show in Barometer
    for col_idx, header in enumerate(headers):
        if col_idx < 3:
            continue
        col_values = [row[col_idx] if col_idx < len(row) else "" for row in all_values[1:]]
        if all(v == "" for v in col_values):
            empty.add(header)
    if empty:
        print(f"→ {len(empty)} colonne(s) vide(s) : {sorted(empty)}")
    return empty


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-week", type=int, default=1)
    parser.add_argument("--start-year", type=int, default=2024)
    args = parser.parse_args()

    print(f"\n🔧 Fix semaines manquantes/vides — W{args.start_week}-{args.start_year}\n")

    ws = get_sheet()
    existing_headers = get_existing_headers(ws)
    empty_cols = get_empty_columns(ws, existing_headers)

    weeks = list(all_weeks_from(args.start_week, args.start_year))
    total = len(weeks)
    print(f"→ {total} semaine(s) à vérifier\n")

    fixed = skipped = not_found = 0

    for i, (w, y) in enumerate(weeks, 1):
        hdr = col_header(w, y)

        if hdr in existing_headers and hdr not in empty_cols:
            skipped += 1
            continue

        print(f"[{i}/{total}] {hdr} — {'colonne vide' if hdr in empty_cols else 'manquante'}")

        if hdr in empty_cols:
            col_idx = existing_headers.index(hdr) + 1
            print(f"  → Suppression colonne vide en {col_index_to_letter(col_idx)}")
            ws.delete_columns(col_idx)
            existing_headers = get_existing_headers(ws)
            time.sleep(1)

        html, page_url = fetch_page(w, y)
        if not html:
            not_found += 1
            time.sleep(1)
            continue

        image_urls = extract_image_urls(html)
        if not image_urls:
            not_found += 1
            time.sleep(1)
            continue

        prices_raw = extract_prices(image_urls)
        if not prices_raw:
            not_found += 1
            time.sleep(1)
            continue

        canonical = get_canonical_products(ws)
        prices = normalize_with_difflib(prices_raw, canonical)

        upsert_week(ws, prices, hdr)
        existing_headers = get_existing_headers(ws)
        fixed += 1
        time.sleep(3)

    print(f"\n✅ Fix terminé.")
    print(f"   Corrigées   : {fixed}")
    print(f"   Déjà bonnes : {skipped}")
    print(f"   Non trouvées: {not_found}\n")


if __name__ == "__main__":
    main()

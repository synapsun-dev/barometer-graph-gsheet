"""
TaiyangNews PV Price Index — Backfill + maintenance complète
-------------------------------------------------------------
Lance en séquence :
  1. Scrape toutes les semaines W1-2024 → aujourd'hui (skip si déjà présentes)
  2. Nettoie les unités résiduelles
  3. Supprime les lignes bloquées

Usage :
    python backfill.py                          # normal : skip semaines existantes
    python backfill.py --force                  # re-scrappe ET écrase toutes les semaines
    python backfill.py --start-week 1 --start-year 2024
    python backfill.py --force --start-week 38 --start-year 2024
"""

import argparse
import logging
import time
from datetime import date

from taiyangnews_pv_scraper import (
    build_url,
    clean_units,
    col_header,
    extract_image_urls,
    extract_prices,
    fetch_page,
    get_canonical_products,
    get_existing_headers,
    get_sheet,
    normalize_with_difflib,
    remove_blocked_rows,
    upsert_week,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def all_weeks_from(start_week: int, start_year: int):
    today = date.today()
    end_week, end_year = today.isocalendar()[1], today.isocalendar()[0]
    w, y = start_week, start_year
    while (y, w) <= (end_year, end_week):
        yield w, y
        last = date(y, 12, 28).isocalendar()[1]
        if w >= last:
            w, y = 1, y + 1
        else:
            w += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-week", type=int, default=1)
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape and overwrite ALL weeks (including already-present ones). "
             "Does not add new products — use after a sheet cleanup.",
    )
    args = parser.parse_args()

    mode = "FORCE (overwrite all)" if args.force else "normal (skip existing)"
    logger.info("Backfill TaiyangNews — W%d-%d → today [%s]", args.start_week, args.start_year, mode)

    if args.force:
        logger.warning(
            "FORCE MODE: all existing week columns will be overwritten with fresh Vision data."
        )

    ws = get_sheet()
    weeks = list(all_weeks_from(args.start_week, args.start_year))
    total = len(weeks)
    logger.info("%d week(s) to process", total)

    existing_headers = get_existing_headers(ws)
    skipped = updated = added = not_found = 0

    for i, (w, y) in enumerate(weeks, 1):
        hdr = col_header(w, y)
        already_present = hdr in existing_headers
        logger.info("[%d/%d] %s%s", i, total, hdr, " (exists)" if already_present else "")

        if already_present and not args.force:
            logger.info("  Already present — skipping")
            skipped += 1
            continue

        html = fetch_page(w, y)
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
        upsert_week(ws, prices, hdr, build_url(w, y), force=args.force)

        if already_present:
            updated += 1
        else:
            added += 1
            existing_headers.append(hdr)

        time.sleep(3)

    if args.force:
        logger.info(
            "Scraping complete: %d updated | %d new | %d not found (404/no images)",
            updated, added, not_found,
        )
    else:
        logger.info(
            "Scraping complete: %d added | %d already present | %d not found",
            added, skipped, not_found,
        )

    remove_blocked_rows(ws)
    clean_units(ws)

    logger.info("Backfill complete.")


if __name__ == "__main__":
    main()

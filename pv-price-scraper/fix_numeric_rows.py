"""
Supprime les lignes dont le nom de produit est un nombre pur (0, 1, 2...28)
Ces lignes sont des artefacts de conversion liste→dict de Claude Vision.

Usage :
    python fix_numeric_rows.py
"""

import json
import os
import time

import gspread
from google.oauth2.service_account import Credentials

from taiyangnews_pv_scraper import SHEET_ID, SHEET_TAB, SCOPES


def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON non définie.")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)


def is_numeric_name(name: str) -> bool:
    """Retourne True si le nom est un nombre pur (ex: '0', '1', '17')."""
    try:
        int(name.strip())
        return True
    except ValueError:
        return False


def main():
    print("\n🧹 Suppression des lignes numériques parasites\n")
    ws = get_sheet()

    col_a = ws.col_values(1)
    if not col_a:
        print("Sheet vide.")
        return

    rows_to_delete = []
    for i, name in enumerate(col_a):
        if i == 0:  # Skip header
            continue
        if name and is_numeric_name(name):
            rows_to_delete.append(i + 1)
            print(f"  → À supprimer : ligne {i+1} — '{name}'")

    if not rows_to_delete:
        print("✅ Aucune ligne numérique trouvée.")
        return

    print(f"\n→ {len(rows_to_delete)} ligne(s) à supprimer...")
    for row_idx in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_idx)
        time.sleep(0.3)

    print(f"✅ {len(rows_to_delete)} ligne(s) supprimée(s).\n")


if __name__ == "__main__":
    main()

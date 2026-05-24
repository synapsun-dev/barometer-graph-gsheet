"""
Réécrit la colonne B (Product) avec la liste complète et correcte des produits.
Liste définie en dur, validée manuellement depuis TaiyangNews.

Usage :
    python fix_product_names.py
"""

import json
import os
import time

import gspread
from google.oauth2.service_account import Credentials

from taiyangnews_pv_scraper import SHEET_ID, SHEET_TAB, SCOPES

# ── LISTE COMPLÈTE VALIDÉE ────────────────────────────────────────────────────
# 35 produits dans l'ordre exact de la colonne B

CORRECT_PRODUCTS = [
    # Polysilicon (lignes 1-5)
    "Reusable Chinese 9N (RMB/kg)",
    "Chinese 9N (RMB/kg)",
    "Global (USD/kg)",
    "N-Type Silicon in China (RMB/kg)",
    "Granular Silicon (RMB/kg)",
    # Wafer (lignes 6-10)
    "p-type, 182mm, 150µm (RMB/piece)",
    "p-type 210mm, 150µm (RMB/piece)",
    "n-type 210mm, 130µm (RMB/piece)",
    "n-type 182mm, 130µm (RMB/piece)",
    "n-type 210R, 130µm (RMB/piece)",
    # Cell (lignes 11-15)
    "PERC bifacial - p-type, 182mm (RMB/W)",
    "PERC bifacial - p-type, 210mm (RMB/W)",
    "TOPCon - n-type 182mm (RMB/W)",
    "TOPCon - n-type, 210mm (RMB/W)",
    "Bifacial 210R TOPCon Cell (Above 24.3%) (RMB/W)",
    # Module (lignes 16-33)
    "PERC monofacial - p-type, 182mm (RMB/W)",
    "PERC bifacial - p-type, 182mm, 72 cells (RMB/W)",
    "PERC bifacial - p-type, 210mm, 55 cells (RMB/W)",
    "TOPCon bifacial - n-type, 182mm, 72 cells (RMB/W)",
    "PERC monofacial - p-type, 182mm (540-550W)/(420-495W) (RMB/W)",
    "PERC bifacial - p-type, 182mm, 72 cells (540-550W)/(540-550W)/(420-495W) (RMB/W)",
    "210mm HJT Module (615-635W) (RMB/W)",
    "TOPCon bifacial - n-type, 210mm, 60 cells (630-655W) (RMB/W)",
    "TOPCon bifacial - n-type, 210mm, 60 cells (700-725W) (RMB/W)",
    "TOPCon bifacial - n-type, 210R, 60 cells (610-635W) (RMB/W)",
    "210mm HJT Module (715-730W) (RMB/W)",
    "BC Module (655W+) (RMB/W)",
    "BC Module (655W+) 210R (RMB/W)",
    # Glass (lignes 34-35)
    "Solar Glass 3.2 mm (RMB/m2)",
    "Solar Glass 2.0mm (RMB/m2)",
]


def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON non définie.")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)


def main():
    print(f"\n🔧 Réécriture colonne B — {len(CORRECT_PRODUCTS)} produit(s)\n")

    ws = get_sheet()
    col_b = ws.col_values(2)
    current = col_b[1:] if len(col_b) > 1 else []
    total = len(current)

    print(f"→ {total} ligne(s) actuellement en colonne B")

    if total != len(CORRECT_PRODUCTS):
        print(f"⚠  Nombre de lignes ({total}) ≠ liste ({len(CORRECT_PRODUCTS)})")
        print("   Les lignes supplémentaires ne seront pas modifiées.")

    corrections = 0
    for i, correct in enumerate(CORRECT_PRODUCTS):
        row_num = i + 2
        current_val = current[i] if i < len(current) else ""
        if current_val != correct:
            ws.update(values=[[correct]], range_name=f"B{row_num}")
            print(f"  ✓ B{row_num}: '{current_val}' → '{correct}'")
            corrections += 1
            time.sleep(0.3)

    print(f"\n✅ {corrections} correction(s) appliquée(s).")

    if total > len(CORRECT_PRODUCTS):
        print(f"\n⚠  {total - len(CORRECT_PRODUCTS)} ligne(s) au-delà de la liste — vérifier manuellement :")
        for i in range(len(CORRECT_PRODUCTS), total):
            print(f"   B{i+2}: '{current[i]}'")


if __name__ == "__main__":
    main()

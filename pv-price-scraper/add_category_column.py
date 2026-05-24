"""
Ajoute la colonne Category (colonne A) au Google Sheet existant.
- Insère une nouvelle colonne A "Category"
- Décale Product en B et toutes les semaines en C+
- Remplit la catégorie de chaque produit via Claude (text, pas Vision)

Usage :
    python add_category_column.py

A lancer UNE SEULE FOIS après le backfill initial.
"""

import json
import os
import re
import time

import anthropic
import gspread
from google.oauth2.service_account import Credentials

from taiyangnews_pv_scraper import SHEET_ID, SHEET_TAB, SCOPES, VALID_CATEGORIES


def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON non définie.")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)


def assign_categories(products: list) -> dict:
    """
    Appel Claude text pour assigner une catégorie à chaque produit.
    Retourne {produit: catégorie}.
    """
    client = anthropic.Anthropic()

    products_str = "\n".join(f"- {p}" for p in products)

    prompt = (
        "Voici une liste de produits photovoltaïques. "
        "Assigne à chacun une catégorie parmi : Polysilicon, Wafer, Cell, Module, Glass.\n\n"
        f"{products_str}\n\n"
        "Règles :\n"
        "- Polysilicon : silicon, poly, granular silicon\n"
        "- Wafer : wafer, µm, piece\n"
        "- Cell : cell, RMB/W (produits de cellules)\n"
        "- Module : module, bifacial, monofacial, HJT, TOPCon (produits finis), BC Module\n"
        "- Glass : glass, verre\n"
        "- Unknown : si aucune catégorie ne correspond\n\n"
        "Retourne UNIQUEMENT un JSON : {\"nom produit\": \"Catégorie\", ...}"
    )

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    try:
        categories = json.loads(raw)
    except json.JSONDecodeError:
        print("⚠ JSON invalide — toutes les catégories = Unknown")
        return {p: "Unknown" for p in products}

    # Valider les catégories
    result = {}
    for product in products:
        cat = categories.get(product, "Unknown")
        result[product] = cat if cat in VALID_CATEGORIES else "Unknown"

    return result


def main():
    print("\n📊 Ajout colonne Category au Google Sheet\n")

    ws = get_sheet()
    headers = ws.row_values(1)

    if headers and headers[0] == "Category":
        print("✅ Colonne Category déjà présente.")
        return

    # Récupérer la liste des produits (actuellement en colonne A)
    col_a = ws.col_values(1)
    products = [p for p in col_a[1:] if p]
    print(f"→ {len(products)} produit(s) à catégoriser")

    # Assigner les catégories via Claude
    print("→ Claude (assignation catégories)...")
    categories = assign_categories(products)

    # Insérer une nouvelle colonne A (décale tout vers la droite)
    # Après insertion : A=Category, B=Product, C=Show in Barometer (décalée), D+=semaines
    print("→ Insertion colonne A 'Category'...")
    ws.insert_cols([["Category"]], col=1)
    time.sleep(2)

    # Écrire le header
    ws.update(values=[["Category"]], range_name="A1")
    time.sleep(1)

    # Les produits sont maintenant en colonne B (après insertion)
    col_b = ws.col_values(2)
    products_in_b = [p for p in col_b[1:] if p]

    category_values = [[categories.get(p, "Unknown")] for p in products_in_b]

    # Écrire par batch
    batch_size = 50
    for i in range(0, len(category_values), batch_size):
        batch = category_values[i:i + batch_size]
        ws.update(values=batch, range_name=f"A{i + 2}")
        time.sleep(1)

    print(f"✅ Colonne Category ajoutée — {len(category_values)} produit(s) catégorisé(s).\n")

    # Afficher le résumé
    from collections import Counter
    counts = Counter(categories.values())
    for cat, count in sorted(counts.items()):
        print(f"   {cat}: {count}")


if __name__ == "__main__":
    main()

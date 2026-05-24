"""
Diagnostique les noms de produits dans le Google Sheet :
1. Lit la colonne B actuelle
2. Récupère la liste de référence depuis TaiyangNews CW19-2026
3. Affiche le mapping et les corrections à apporter
4. Applique les corrections si --fix est passé

Usage :
    python diagnose_products.py          # Diagnostic seul
    python diagnose_products.py --fix    # Diagnostic + correction
"""

import argparse
import base64
import json
import os
import re
import time

import anthropic
import gspread
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

from taiyangnews_pv_scraper import SHEET_ID, SHEET_TAB, SCOPES, image_to_base64


def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON non définie.")
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)


def get_reference_products() -> list:
    """
    Récupère la liste complète et ordonnée des produits
    depuis l'image CW19-2026 via Claude Vision.
    """
    # Télécharger la page
    url = "https://taiyangnews.info/price-index/taiyangnews-pv-price-index-cw19-2026"
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    html = resp.text

    # Extraire l'URL de l'image du tableau
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            u = img.get(attr, "")
            if "media.assettype.com/taiyangnews" in u and "ogImage=true" not in u:
                found.add(u if not u.startswith("//") else "https:" + u)

    pattern = r'https://media\.assettype\.com/taiyangnews[^"\'> \\]+\.(?:png|jpg|jpeg)'
    for u in re.findall(pattern, html):
        found.add(u)

    image_urls = [u.split("?")[0] for u in found if "ogImage=true" not in u][:3]

    if not image_urls:
        print("✗ Aucune image trouvée pour CW19-2026")
        return []

    client = anthropic.Anthropic()
    content = []
    for url in image_urls:
        print(f"  → Image : {url.split('/')[-1][:50]}")
        b64, media_type = image_to_base64(url)
        content.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}})

    content.append({
        "type": "text",
        "text": (
            "Tableau de prix PV. Liste TOUS les noms de produits dans l'ordre exact "
            "du tableau (de haut en bas), y compris ceux avec un tiret (-).\n"
            "Inclure l'unité dans le nom entre parenthèses.\n"
            "Exclure les lignes de catégorie (Polysilicon RMB/kg, Wafer RMB/piece, etc.).\n"
            "Exclure les lignes 'China Project'.\n\n"
            "Retourne UNIQUEMENT une liste JSON de strings ordonnée :\n"
            "[\"Produit 1 (unité)\", \"Produit 2 (unité)\", ...]"
        )
    })

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": content}]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    products = json.loads(raw)
    return [p for p in products if isinstance(p, str) and len(p) > 3]


def is_truncated(name: str) -> bool:
    if not name or name.strip() == "":
        return False
    try:
        float(name.strip())
        return True
    except ValueError:
        pass
    return len(name.strip()) < 5


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Appliquer les corrections")
    args = parser.parse_args()

    print("\n🔍 Diagnostic des noms de produits\n")

    ws = get_sheet()

    # Lire colonnes A et B
    col_a = ws.col_values(1)
    col_b = ws.col_values(2)

    categories = col_a[1:] if len(col_a) > 1 else []
    products = col_b[1:] if len(col_b) > 1 else []

    print(f"→ {len(products)} produit(s) en colonne B")
    print("\nColonne B actuelle :")
    for i, p in enumerate(products, 1):
        status = " ⚠ TRONQUÉ" if is_truncated(p) else ""
        print(f"  {i:2}. {p}{status}")

    # Récupérer la liste de référence depuis CW19-2026
    print("\n→ Récupération liste de référence depuis CW19-2026...")
    reference = get_reference_products()
    print(f"→ {len(reference)} produit(s) de référence trouvé(s)")
    print("\nListe de référence CW19-2026 :")
    for i, p in enumerate(reference, 1):
        print(f"  {i:2}. {p}")

    # Construire le mapping corrections
    print("\n\n📋 CORRECTIONS PROPOSÉES :")
    corrections = {}

    # Trouver les ancres (produits non tronqués) pour aligner
    anchors_b = {i: p for i, p in enumerate(products) if not is_truncated(p) and p.strip()}

    for i, current in enumerate(products):
        if not is_truncated(current):
            continue

        # Chercher dans la référence par position relative
        prev_idx = max((j for j in anchors_b if j < i), default=None)
        if prev_idx is not None:
            prev_name = anchors_b[prev_idx]
            try:
                ref_pos = next(j for j, r in enumerate(reference)
                               if r.strip().lower() == prev_name.strip().lower())
                offset = i - prev_idx
                candidate_pos = ref_pos + offset
                if 0 <= candidate_pos < len(reference):
                    candidate = reference[candidate_pos]
                    corrections[i] = candidate
                    print(f"  Ligne {i+2:2} B{i+2}: '{current}' → '{candidate}'")
            except StopIteration:
                print(f"  Ligne {i+2:2} B{i+2}: '{current}' → ??? (ancre '{prev_name}' non trouvée dans référence)")

    if args.fix and corrections:
        print(f"\n→ Application de {len(corrections)} correction(s)...")
        for i, correct_name in sorted(corrections.items()):
            ws.update(values=[[correct_name]], range_name=f"B{i+2}")
            time.sleep(0.3)
        print("✅ Corrections appliquées.\n")
    elif not args.fix:
        print("\n💡 Lancez avec --fix pour appliquer les corrections.")


if __name__ == "__main__":
    main()

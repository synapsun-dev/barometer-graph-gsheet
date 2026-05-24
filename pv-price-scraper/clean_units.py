"""
TaiyangNews PV Price Index — Nettoyage des unités dans le Google Sheet
-----------------------------------------------------------------------
Parcourt toutes les cellules de données et extrait uniquement la valeur
numérique (supprime les unités résiduelles comme "38.5 RMB/kg" → "38.5").

Usage :
    python clean_units.py
"""

from taiyangnews_pv_scraper import clean_units, get_sheet

if __name__ == "__main__":
    clean_units(get_sheet())

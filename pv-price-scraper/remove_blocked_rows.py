"""
Supprime du Google Sheet les lignes correspondant aux produits de la liste de blocage.

Usage :
    python remove_blocked_rows.py
"""

from taiyangnews_pv_scraper import get_sheet, remove_blocked_rows

if __name__ == "__main__":
    remove_blocked_rows(get_sheet())

# barometer-graph-gsheet — Barometer Synapsun PV Price Index

Graphic Automatic BOM modules from Tayang data

---

## Rôle de ce dossier

**Clone officiel** du repo GitHub [`synapsun-dev/barometer-graph-gsheet`](https://github.com/synapsun-dev/barometer-graph-gsheet) (anciennement `it-dev-synapsun/graph-gsheet-tayang`, renommé le 2026-06-10).

C'est la **source de vérité** du projet Barometer Synapsun. Toutes les modifications
doivent être faites ici et poussées sur GitHub pour que le GitHub Actions CI/CD les prenne en compte.

---

## Relation avec `C:\claude\Synapsun\Barometer\`

| Critère | `repo-clone` (ce dossier) | `Barometer/` |
|---|---|---|
| Type | Clone GitHub officiel ✅ | Copie de travail locale |
| Remote GitHub | `synapsun-dev/barometer-graph-gsheet` | Aucun remote configuré |
| Scraper | `pv-price-scraper/taiyangnews_pv_scraper.py` | `taiyangnews_pv_scraper.py` (racine) |
| Scraper (taille) | 23 944 bytes ✅ | 21 808 bytes |
| Scraper (modifié) | 2026-06-01 ✅ | 2026-05-25 |
| `barometre-synapsun.html` | 86 578 bytes / 2026-06-01 ✅ | 83 701 bytes / 2026-05-27 |
| Commits git | 5+ (fixes URL, model, iframe) | 1 seul (« init état initial ») |

**Verdict :** `Barometer/` est un **snapshot créé avant le clonage GitHub**. Il est désormais
obsolète sur les deux fichiers critiques (scraper +2136 bytes de retard, barometre.html +2877 bytes
de retard). Pour toute modification, utiliser **uniquement `repo-clone`** et pousser sur GitHub.

---

## Structure du repo

```
repo-clone/
├── pv-price-scraper/           ← Scripts Python (scraper + maintenance)
│   ├── taiyangnews_pv_scraper.py   ← Scraper principal (hebdomadaire)
│   ├── backfill.py
│   ├── requirements.txt
│   └── ...
├── .github/
│   └── workflows/pv_price_weekly.yml  ← GitHub Actions (lundi 8h UTC)
├── index.html                  ← Dashboard principal
├── barometre-synapsun.html     ← Dashboard SEO alternatif
└── README.md                   ← Ce fichier
```

---

## Commandes courantes

```bash
# Installer les dépendances
pip install -r pv-price-scraper/requirements.txt

# Lancer le scraper manuellement
python pv-price-scraper/taiyangnews_pv_scraper.py

# Backfill historique
python pv-price-scraper/backfill.py
```

---

*Dernière mise à jour de ce README : 2026-06-04*

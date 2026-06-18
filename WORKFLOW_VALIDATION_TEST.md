# PLAN DE TEST — Workflow pv_price_weekly.yml

**Objectif :** Valider la configuration, la syntaxe YAML, les conditions logiques, les triggers et l'exécution du workflow GitHub Actions `pv_price_weekly.yml`.

**Date de test :** 2026-06-18  
**Composant validé :** Test 7 (GitHub Actions Workflows) du TEST_PLAN.md

---

## Tests à valider

### Test W.1 — Validation syntaxe YAML
- **Cas** : Syntaxe YAML correcte (structure, indentation, caractères spéciaux)
- **Exécution** :
  1. Charger le fichier `.github/workflows/pv_price_weekly.yml`
  2. Vérifier que YAML parse sans erreur
  3. Vérifier que toutes les clés attendues sont présentes
- **Résultat attendu** :
  - YAML valide (pas d'erreur parse)
  - Structure : `on`, `jobs`, `steps` présents
  - Concurrency block présent

### Test W.2 — Validation du trigger CRON (lundi 08:00 UTC)
- **Cas** : Trigger cron configuré pour lundi 8h UTC uniquement
- **Exécution** :
  1. Vérifier que `on.schedule.cron` = "0 8 * * 1"
  2. Vérifier que cron déclenche le lundi (jour 1 de la semaine)
  3. Vérifier que cron déclenche à 08:00 UTC exactement
- **Résultat attendu** :
  - Cron: "0 8 * * 1" ✓
  - Minute: 0 (00:00) ✓
  - Heure: 8 (08:00 UTC) ✓
  - Jour de la semaine: 1 (lundi) ✓

### Test W.3 — Validation workflow_dispatch (trigger manuel)
- **Cas** : Workflow peut être déclenché manuellement avec inputs optionnels
- **Exécution** :
  1. Vérifier que `workflow_dispatch` est présent
  2. Vérifier que 3 inputs sont configurés : mode, week, year
  3. Vérifier que mode a 3 options : weekly, backfill, force
  4. Vérifier que week et year sont optionnels (required: false)
  5. Vérifier que mode par défaut = "weekly"
- **Résultat attendu** :
  - workflow_dispatch présent ✓
  - mode = choice avec options [weekly, backfill, force] ✓
  - week = string, required: false ✓
  - year = string, required: false ✓
  - mode default: "weekly" ✓

### Test W.4 — Validation concurrency (une exécution à la fois)
- **Cas** : Concurrency bloque les exécutions parallèles sur le même groupe
- **Exécution** :
  1. Vérifier que `concurrency.group` = "pv-scraper"
  2. Vérifier que `concurrency.cancel-in-progress` = false (ne pas tuer les runs en cours)
- **Résultat attendu** :
  - concurrency.group: "pv-scraper" ✓
  - cancel-in-progress: false ✓

### Test W.5 — Validation steps — Checkout
- **Cas** : Step 1 "Checkout repo" clone le repo
- **Exécution** :
  1. Vérifier que step utilise actions/checkout@v4
  2. Vérifier que persist-credentials: false (pas de creds stockées)
- **Résultat attendu** :
  - uses: actions/checkout@v4 ✓
  - persist-credentials: false ✓

### Test W.6 — Validation steps — Setup Python
- **Cas** : Step 2 setup Python 3.11
- **Exécution** :
  1. Vérifier que step utilise actions/setup-python@v5
  2. Vérifier que python-version = "3.11"
- **Résultat attendu** :
  - uses: actions/setup-python@v5 ✓
  - python-version: "3.11" ✓

### Test W.7 — Validation steps — Install dependencies
- **Cas** : Step 3 installe requirements.txt
- **Exécution** :
  1. Vérifier que step exécute `pip install -r pv-price-scraper/requirements.txt`
  2. Vérifier que tous les packages sont définis dans requirements.txt
- **Résultat attendu** :
  - Command: pip install -r pv-price-scraper/requirements.txt ✓
  - anthropic, gspread, google-auth, requests, beautifulsoup4, tenacity présents ✓

### Test W.8 — Validation mode FORCE (--force backfill)
- **Cas** : Si mode == 'force', exécute `backfill.py --force`
- **Exécution** :
  1. Vérifier la condition `if: ${{ github.event.inputs.mode == 'force' }}`
  2. Vérifier que la commande exécutée est `cd pv-price-scraper && python backfill.py --force`
  3. Vérifier que secrets sont passés : GOOGLE_CREDENTIALS_JSON, ANTHROPIC_API_KEY
- **Résultat attendu** :
  - if condition correcte ✓
  - Commande: `cd pv-price-scraper && python backfill.py --force` ✓
  - Secrets env vars présents ✓

### Test W.9 — Validation mode BACKFILL
- **Cas** : Si mode == 'backfill', exécute `backfill.py` (sans --force)
- **Exécution** :
  1. Vérifier la condition `if: ${{ github.event.inputs.mode == 'backfill' }}`
  2. Vérifier que la commande exécutée est `cd pv-price-scraper && python backfill.py`
  3. Vérifier que secrets sont passés
- **Résultat attendu** :
  - if condition correcte ✓
  - Commande: `cd pv-price-scraper && python backfill.py` ✓
  - Secrets env vars présents ✓

### Test W.10 — Validation mode WEEKLY (par défaut)
- **Cas** : Si mode == 'weekly' (ou vide), exécute scraper nominal avec args optionnels
- **Exécution** :
  1. Vérifier la condition `if: ${{ github.event.inputs.mode != 'backfill' && github.event.inputs.mode != 'force' }}`
  2. Vérifier que les args --week et --year sont construits conditionnellement
  3. Vérifier que la commande exécutée est `cd pv-price-scraper && python taiyangnews_pv_scraper.py $ARGS`
- **Résultat attendu** :
  - if condition correcte ✓
  - Args conditionnels construits ✓
  - Commande correcte ✓

### Test W.11 — Validation secrets GitHub (simulation)
- **Cas** : Secrets GOOGLE_CREDENTIALS_JSON et ANTHROPIC_API_KEY sont accessible au workflow
- **Exécution** :
  1. Vérifier que secrets.GOOGLE_CREDENTIALS_JSON est référencé dans l'env
  2. Vérifier que secrets.ANTHROPIC_API_KEY est référencé dans l'env
  3. Vérifier que ces env vars sont visibles dans les 3 modes (force, backfill, weekly)
- **Résultat attendu** :
  - GOOGLE_CREDENTIALS_JSON dans tous les 3 steps ✓
  - ANTHROPIC_API_KEY dans tous les 3 steps ✓

### Test W.12 — Simulation locale — Mode WEEKLY nominal
- **Cas** : Exécuter le scraper en mode nominal (semaine actuelle)
- **Exécution** :
  1. Installer dependencies : `pip install -r pv-price-scraper/requirements.txt`
  2. Exécuter : `cd pv-price-scraper && python taiyangnews_pv_scraper.py` (sans args, utilise semaine actuelle)
  3. Vérifier que le scraper s'exécute sans erreur (mode nominal)
- **Résultat attendu** :
  - Exit code 0 (succès)
  - Au moins 1 semaine extraite
  - Google Sheets reçoit les données (ou simulation locale)

### Test W.13 — Simulation locale — Mode WEEKLY avec args custom
- **Cas** : Exécuter le scraper avec --week et --year spécifiés
- **Exécution** :
  1. Exécuter : `cd pv-price-scraper && python taiyangnews_pv_scraper.py --week 22 --year 2024`
  2. Vérifier que la semaine W22-2024 est scrapée
- **Résultat attendu** :
  - Exit code 0
  - Colonne W22-2024 remplie dans Google Sheets

### Test W.14 — Historique des runs GitHub Actions
- **Cas** : Vérifier les runs historiques du workflow dans GitHub
- **Exécution** :
  1. Accéder à : https://github.com/synapsun-dev/barometer-graph-gsheet/actions/workflows/pv_price_weekly.yml
  2. Vérifier que les 4 derniers runs sont visibles
  3. Vérifier le statut : completed, success ou failed
  4. Vérifier que chaque run affiche :
     - Timestamp de lancement
     - Trigger (scheduled lundi ou manual dispatch)
     - Conclusion (success/failure)
- **Résultat attendu** :
  - 4+ runs visibles ✓
  - Au moins 1 run avec status "completed" et conclusion "success" ✓
  - Au moins 1 run avec trigger "scheduled" (lundi) ✓

### Test W.15 — Validation des logs du dernier run réussi
- **Cas** : Consulter les logs du dernier run pv_price_weekly.yml réussi
- **Exécution** :
  1. Cliquer sur le run "success" le plus récent
  2. Dérouler le job "scrape-and-update"
  3. Vérifier les logs de chaque step :
     - Checkout repo : "downloaded X commits"
     - Setup Python : "Successfully setup python 3.11"
     - Install dependencies : "Successfully installed anthropic gspread..."
     - Run weekly scraper : "W[n]-[y]: extracted X products, upsert OK" (ou équivalent)
  4. Vérifier qu'aucune erreur 🔴 n'apparaît
- **Résultat attendu** :
  - Tous les steps ont statut "✓"
  - Aucune erreur dans les logs
  - Message succès du scraper visible

### Test W.16 — Validation concurrency — Run parallèle bloqué
- **Cas** : Si un run est en cours, un deuxième run du même workflow doit attendre
- **Exécution** :
  1. Déclencher manuellement le workflow (workflow_dispatch)
  2. Immédiatement après, déclencher un 2ème run manuellement
  3. Vérifier que le 2ème run attend le 1er (statut "queued")
  4. Vérifier que cancel-in-progress: false (ne pas tuer le 1er run)
- **Résultat attendu** :
  - 1er run : "in progress"
  - 2ème run : "queued"
  - Après 1er run : 2ème run commence
  - Aucun run n'est cancellé

---

## EXÉCUTION DES TESTS

### Résultats validés

[À remplir lors de l'exécution]


# TEST_PLAN.md — Barometer (Synapsun PV Price Index)

## Vue d'ensemble

Ce document définit les cas de test obligatoires pour valider chaque composant du pipeline Barometer avant toute mise en production. Les tests sont organisés par **composant** et couvrent :
- **Cas nominaux** : flux happy path attendu
- **Cas limites** : comportement aux frontières des paramètres
- **Cas d'erreur** : gestion des pannes et données invalides

**Note d'exécution** : les tests sont exécutés dans l'ordre listé. Un test marqué `[SKIP]` nécessite des resources externes (API, Google Sheets, GitHub Actions) non accessibles en local.

---

## Composant 1 : taiyangnews_pv_scraper.py (Scraper principal)

**Responsabilité** : Scraper TaiyangNews chaque lundi 8h UTC, extraire les prix via Claude Vision, normaliser les produits, upsert dans Google Sheets.

### Test 1.1 — Scraper nominal (semaine complète avec 15+ produits)
- **Cas** : Cas nominal — semaine publiée avec tous les produits attendus
- **Exécution** :
  1. Lancer : `python taiyangnews_pv_scraper.py --week 25 --year 2024`
  2. Vérifier que le scraper scrape la page TaiyangNews W25-2024
  3. Vérifier que 15+ images de prix sont extraites
  4. Vérifier que Claude Vision extrait les prix (au moins 1 ligne JSON retournée)
  5. Vérifier que Google Sheets reçoit les données (colonne W25-2024 remplie)
- **Résultat attendu** :
  - Stdout : "W25-2024: extracted ≥15 products, upsert OK"
  - Google Sheets : colonne W25-2024 non vide, URL en ligne 2
  - Exit code : 0

### Test 1.2 — Scraper avec produits doublons (Solar Glass variants)
- **Cas** : Limite — produits doublons (ex: Solar Glass 3.2mm et 3.2 mm) doivent être fusionnés
- **Exécution** :
  1. Déclencher le scraper sur une semaine contenant Solar Glass 3.2mm et Solar Glass 3.2 mm
  2. Vérifier que les deux sont normalisés en un seul produit canonical
  3. Vérifier que difflib.SequenceMatcher fusion à 82% de similarité
- **Résultat attendu** :
  - Google Sheets : une seule ligne "Solar Glass 3.2 mm" avec un prix, pas de doublons
  - Logs : "Merged X duplicates via difflib"

### Test 1.3 — Scraper avec produits bloqués
- **Cas** : Limite — produits figurant dans BLOCKED_PRODUCTS ne doivent pas être écrit
- **Exécution** :
  1. Vérifier que la liste BLOCKED_PRODUCTS est chargée (16 produits attendus)
  2. Simuler une extraction Vision contenant "china project", "hjt module m10"
  3. Vérifier que ces produits ne sont pas écrit dans Google Sheets
- **Résultat attendu** :
  - Google Sheets : zéro ligne contenant "china project" ou "hjt module m10"
  - Logs : "Filtered out X blocked products"

### Test 1.4 — Scraper avec fallback semaine précédente
- **Cas** : Limite — si la page de la semaine courante n'existe pas, fallback W-1
- **Exécution** :
  1. Lancer avec `--week X --year 2026` où la semaine X n'existe pas encore
  2. Vérifier que le scraper retente W(X-1)-2026
  3. Vérifier que le sheet reçoit les données de W(X-1)-2026, pas W(X)-2026
- **Résultat attendu** :
  - Google Sheets : données dans la colonne W(X-1)-2026, pas W(X)-2026
  - Logs : "URL W[X]-2026 not found, trying W[X-1]-2026..."
  - Exit code : 0

### Test 1.5 — Scraper avec format URL multi-année
- **Cas** : Limite — URL change entre 2024/2025 (pattern `year-cwN`) et 2026+ (pattern `cwN-year`)
- **Exécution** :
  1. Lancer scraper pour W1-2024 (attend format `2024-cw1`)
  2. Lancer scraper pour W25-2026 (attend format `cw25-2026`)
  3. Vérifier que les deux formats retournent une page
- **Résultat attendu** :
  - Deux runs successifs = deux colonnes remplies dans le Sheet
  - Logs : "Built URL {year}-cw{week}" pour 2024, "cwN-year" pour 2026

### Test 1.6 — Vision extraction avec catégories inconnues
- **Cas** : Limite — produit sans catégorie reconnue → catégorie "Unknown"
- **Exécution** :
  1. Simuler une réponse Vision avec produit sans catégorie
  2. Vérifier que le produit reçoit category="Unknown"
  3. Vérifier que le produit est écrit dans Google Sheets
- **Résultat attendu** :
  - Google Sheets : ligne avec category="Unknown" présente

### Test 1.7 — Vision extraction avec prix hors limites (sanity bounds)
- **Cas** : Erreur — prix > 500 USD/kg (Polysilicon) → rejeté, log warning
- **Exécution** :
  1. Simuler une réponse Vision avec prix=999 pour Polysilicon
  2. Vérifier que le prix est rejeté (hors PRICE_BOUNDS)
  3. Vérifier que le produit ne figure pas dans Google Sheets
- **Résultat attendu** :
  - Google Sheets : produit absent ou prix vide
  - Logs : "Price out of bounds: 999 (Polysilicon, bounds 5.0-500.0)"

### Test 1.8 — Google Sheets authentication failure
- **Cas** : Erreur — `GOOGLE_CREDENTIALS_JSON` manquant ou invalide
- **Exécution** :
  1. Retirer/invalider GOOGLE_CREDENTIALS_JSON du fichier .env ou secrets
  2. Lancer le scraper
  3. Vérifier que le scraper échoue avec exit code 1
- **Résultat attendu** :
  - Logs : "Failed to authenticate: Google credentials missing"
  - Exit code : 1

### Test 1.9 — API Claude Vision timeout
- **Cas** : Erreur — appel Vision prend >300s (timeout réseau)
- **Exécution** :
  1. Simuler un timeout API Anthropic (delay > 300s)
  2. Vérifier que le scraper retry 3 fois (hardcoded)
  3. Vérifier que le scraper échoue après 3 tentatives
- **Résultat attendu** :
  - Logs : "Vision call timeout, attempt 1/3", puis "2/3", puis "3/3"
  - Exit code : 1 après épuisement des tentatives

### Test 1.10 — Sheet minimum products check (< 10 produits)
- **Cas** : Erreur — Vision extrait < 10 produits (MIN_EXPECTED_PRODUCTS=10)
- **Exécution** :
  1. Simuler une page TaiyangNews minimale (5 images/produits)
  2. Vérifier que le scraper refuse l'upsert et exit(1)
  3. Vérifier que Google Sheets n'est pas modifié
- **Résultat attendu** :
  - Logs : "Extracted only 5 products (min 10), not upserting"
  - Exit code : 1
  - Google Sheets : colonne semaine reste vide

### Test 1.11 — Column header normalization (W1-2024 format)
- **Cas** : Nominal — en-têtes colonnes respectent le format `W{n}-{yyyy}`
- **Exécution** :
  1. Créer nouvelle colonne vide dans Google Sheets
  2. Lancer scraper avec week=5 year=2024
  3. Vérifier que l'en-tête créé est exactement "W5-2024"
- **Résultat attendu** :
  - Google Sheets ligne 1 colonne N : "W5-2024"
  - Ligne 2 colonne N : URL TaiyangNews correspondante

---

## Composant 2 : backfill.py (Backfill + maintenance)

**Responsabilité** : Re-scraper l'historique complet W1-2024 → aujourd'hui, optionnellement en mode FORCE (réécrit toutes les semaines), puis nettoie unités et bloqués.

### Test 2.1 — Backfill nominal (skip semaines existantes)
- **Cas** : Cas nominal — W1-2024 à W10-2024 existent, backfill tente W11+ uniquement
- **Exécution** :
  1. Vérifier que Google Sheets a colonnes W1-2024 … W10-2024 (données présentes)
  2. Lancer : `python backfill.py --start-week 1 --start-year 2024`
  3. Vérifier que le backfill saute W1-2024 … W10-2024 (check "already present")
  4. Vérifier que le backfill scrape W11-2024, W12-2024, etc. jusqu'à aujourd'hui
  5. Vérifier que clean_units() tourne après le scraping
  6. Vérifier que remove_blocked_rows() tourne en dernier
- **Résultat attendu** :
  - Logs : "W1-2024: already present, skipping" × 10
  - Logs : "W11-2024: extracting...", "W12-2024: extracting...", etc.
  - Google Sheets : nouvelles colonnes W11+ remplies

### Test 2.2 — Backfill FORCE mode (réécrit toutes les semaines)
- **Cas** : Limite — `--force` doit récraper et écraser TOUTES les semaines
- **Exécution** :
  1. Enregistrer snapshot Google Sheets (W1-2024, W2-2024, prix actuels)
  2. Lancer : `python backfill.py --force --start-week 1 --start-year 2024`
  3. Vérifier que le backfill traite W1-2024 (pas "already present", mais "extracting...")
  4. Attendre que le run se termine (peut prendre 30+ min pour 100+ semaines)
  5. Comparer Google Sheets avant/après : prix de W1-2024 doivent changer (Vision nouvelle extraction)
- **Résultat attendu** :
  - Logs : "W1-2024: extracting..." (pas "already present")
  - Google Sheets W1-2024 prix : nouveaux (différents du snapshot)
  - Exit code : 0 à la fin

### Test 2.3 — Backfill avec --start-week/--start-year custom
- **Cas** : Nominal — démarrer le backfill à partir d'une semaine spécifique
- **Exécution** :
  1. Lancer : `python backfill.py --start-week 20 --start-year 2024`
  2. Vérifier que le backfill démarre W20-2024 (pas W1-2024)
  3. Vérifier que W1-2024 … W19-2024 ne sont pas retraitées
- **Résultat attendu** :
  - Logs : "Backfill TaiyangNews — W20-2024 → today"
  - Aucune ligne "W1-2024...", "W2-2024...", etc. avant W20-2024

### Test 2.4 — Backfill avec semaine du 28 décembre (année courante → suivante)
- **Cas** : Limite — transition année (W52 2024 → W1 2025)
- **Exécution** :
  1. Lancer backfill avec --start-week 50 --start-year 2024
  2. Vérifier que le backfill gère la transition W52-2024 → W1-2025 → ...
  3. Vérifier qu'aucune semaine n'est sautée
- **Résultat attendu** :
  - Logs contiennent "W50-2024", "W51-2024", "W52-2024", "W1-2025", etc. (séquence complète)

---

## Composant 3 : health_check.py (Vérification quotidienne)

**Responsabilité** : Chaque jour 07:00 UTC, vérifie que les 6 sources (Google Sheets, GitHub Pages, 2 Zoho iframes, BCE, argent XAG, TaiyangNews) répondent.

### Test 3.1 — Health check nominal (tous les checks OK)
- **Cas** : Cas nominal — tous les 6 services répondent avec status 200
- **Exécution** :
  1. Lancer : `python health_check.py`
  2. Vérifier que chacun des 6 checks affiche "✓" ou "OK"
  3. Vérifier exit code 0
- **Résultat attendu** :
  - Logs :
    ```
    Google Sheets CSV: ✓
    GitHub Pages dashboard: ✓
    Zoho Analytics — Sea freight: ✓
    Zoho Analytics — Vue 2: ✓
    ECB exchange rates: ✓
    XAG silver prices: ✓
    ```
  - Exit code : 0

### Test 3.2 — Google Sheets fraîcheur (dernière colonne)
- **Cas** : Nominal — dernière colonne ≤ 2 semaines de retard ISO
- **Exécution** :
  1. Vérifier que Google Sheets a dernière colonne W[current_week]-[current_year]
  2. Lancer health check
  3. Vérifier qu'il ne déclenche pas d'alerte fraîcheur
- **Résultat attendu** :
  - Logs : "Last column W[current_week]-[current_year]: age=0 weeks, OK"

### Test 3.3 — Google Sheets fraîcheur (> 2 semaines retard)
- **Cas** : Limite — dernière colonne > 2 semaines de retard → alerte
- **Exécution** :
  1. Manuellement, dans Google Sheets, renommer dernière colonne W[N-3]-[year] (3 semaines passées)
  2. Lancer health check
  3. Vérifier qu'il détecte l'alerte et exit(1)
- **Résultat attendu** :
  - Logs : "Last column W[N-3]-[year]: age=3 weeks, STALE (max 2)"
  - Exit code : 1

### Test 3.4 — GitHub Pages 404
- **Cas** : Erreur — dashboard GitHub Pages retourne 404
- **Exécution** :
  1. Temporairement renommer `barometre-synapsun.html` en GitHub repo remote
  2. Lancer health check (il tentara `https://synapsun-dev.github.io/barometer-graph-gsheet/`)
  3. Vérifier qu'il détecte 404
- **Résultat attendu** :
  - Logs : "GitHub Pages dashboard: HTTP 404, FAILED"
  - Exit code : 1

### Test 3.5 — Zoho iframe timeout
- **Cas** : Erreur — Zoho Analytics retourne un timeout (>30s)
- **Exécution** :
  1. Simuler un timeout Zoho (bloquer le domaine analytics.zoho.com, ou timeout réseau)
  2. Lancer health check avec retry 3x et delay 15s
  3. Vérifier qu'après 3 tentatives, l'alerte est déclenché
- **Résultat attendu** :
  - Logs : "Zoho Analytics — Sea freight: timeout (attempt 1/3)... timeout (attempt 3/3), FAILED"
  - Exit code : 1

### Test 3.6 — XAG API fallback (jsDelivr → Cloudflare)
- **Cas** : Nominal — si jsDelivr échoue, fallback Cloudflare réussit
- **Exécution** :
  1. Bloquer temporairement jsDelivr (cdn.jsdelivr.net)
  2. Lancer health check
  3. Vérifier qu'il tente jsDelivr, échoue, puis tente Cloudflare (latest.currency-api.pages.dev)
  4. Vérifier qu'il affiche "OK" en final (fallback réussi)
- **Résultat attendu** :
  - Logs : "XAG silver prices: jsDelivr failed, trying Cloudflare... OK"
  - Exit code : 0

---

## Composant 4 : Scripts de maintenance (clean_units.py, diagnose_products.py, etc.)

**Responsabilité** : Nettoyer/diagnostiquer le Google Sheet après scraping (unités résiduelles, noms tronqués, doublons bloqués, etc.).

### Test 4.1 — clean_units.py (suppression unités résiduelles)
- **Cas** : Nominal — cellules contenant "$/kg" ou "RMB/kg" sont nettoyées
- **Exécution** :
  1. Manuellement ajouter une cellule de prix contenant "45.2 $/kg"
  2. Lancer : `python pv-price-scraper/clean_units.py`
  3. Vérifier que la cellule devient "45.2" (unité supprimée)
- **Résultat attendu** :
  - Google Sheets : cellule affiche "45.2" uniquement, pas d'unité

### Test 4.2 — diagnose_products.py (détection produits tronqués)
- **Cas** : Nominal — log les produits > 50 caractères ou mal formés
- **Exécution** :
  1. Lancer : `python pv-price-scraper/diagnose_products.py`
  2. Vérifier qu'il liste tous les produits uniques du sheet
  3. Vérifier qu'il flag les anomalies (ex: "Polysilicon (new) (new) (new)..." = répétitions)
- **Résultat attendu** :
  - Logs : "[ANOMALY] Polysilicon (new) (new) (new)... — length 60, repeated token"

### Test 4.3 — fix_missing_weeks.py (re-scrape colonnes vides)
- **Cas** : Nominal — si une colonne W[N]-[Y] existe mais est vide, re-scrape
- **Exécution** :
  1. Manuellement créer une colonne W20-2024 vide (en-tête seulement)
  2. Lancer : `python pv-price-scraper/fix_missing_weeks.py`
  3. Vérifier que la colonne W20-2024 est remplie avec les prix
- **Résultat attendu** :
  - Google Sheets W20-2024 : non plus vide, 15+ produits avec prix

### Test 4.4 — remove_blocked_rows.py (suppression produits bloqués)
- **Cas** : Nominal — produits listés dans BLOCKED_PRODUCTS sont supprimés
- **Exécution** :
  1. Manuellement ajouter une ligne "hjt module m10 | 5.2" au sheet
  2. Lancer : `python pv-price-scraper/remove_blocked_rows.py`
  3. Vérifier que la ligne "hjt module m10" est supprimée
- **Résultat attendu** :
  - Google Sheets : zéro ligne "hjt module m10"
  - Logs : "Removed 1 blocked product(s)"

### Test 4.5 — fix_product_names.py (normalisation produits)
- **Cas** : Nominal — applique l'alias hardcoded PRODUCT_ALIASES
- **Exécution** :
  1. Manuellement ajouter une ligne "3.2mm (rmb/m2) | 12.5" (alias clé)
  2. Lancer : `python pv-price-scraper/fix_product_names.py`
  3. Vérifier que "3.2mm (rmb/m2)" devient "Solar Glass 3.2 mm (RMB/m2)"
- **Résultat attendu** :
  - Google Sheets : produit renommé en "Solar Glass 3.2 mm (RMB/m2)"

---

## Composant 5 : Dashboards HTML (index.html, barometre-synapsun.html)

**Responsabilité** : Charger et afficher les données PV de Google Sheets CSV, avec graphiques Chart.js interactifs et cartes KPI mises à jour hebdo.

### Test 5.1 — Dashboard charge CSV et affiche données
- **Cas** : Nominal — dashboard se charge, CSV Google Sheets est parsé, 5+ graphiques visibles
- **Exécution** :
  1. Ouvrir `index.html` ou `barometre-synapsun.html` dans navigateur (Chrome)
  2. Vérifier que la page charge sans erreur (console vide de logs d'erreur 🔴)
  3. Vérifier que 5+ graphiques Chart.js sont visibles (Polysilicon, Wafer, Cell, Module, Glass)
  4. Vérifier que les données affichées correspondent à Google Sheets (dates W1-2024 … W[current])
- **Résultat attendu** :
  - Page charge en < 3 secondes
  - Console : zéro erreur 🔴 (erreurs 🟠 warnings acceptées)
  - Graphiques : lignes colorées, points de données visibles

### Test 5.2 — KPI cards affichent dernier prix et variation %
- **Cas** : Nominal — KPI cards montrent "Polysilicon: 123.45 $/kg, -2.3% vs semaine précédente"
- **Exécution** :
  1. Ouvrir dashboard
  2. Identifier les KPI cards (4-5 cards, 1 par catégorie)
  3. Vérifier que chaque card affiche :
     - Nom du produit
     - Dernier prix (2 décimales)
     - Variation % (haussière 🔴, baissière 🟢, stable ⚪)
     - Semaine/année correspondante
- **Résultat attendu** :
  - Card "Polysilicon: 123.45 $/kg" visible
  - "- 2.3 %" affiché en rouge (baisse)

### Test 5.3 — Graphique Polysilicon affiche dernières 12 semaines
- **Cas** : Nominal — zoom sur 3 derniers mois (12 semaines)
- **Exécution** :
  1. Ouvrir dashboard
  2. Identifier graphique "Polysilicon"
  3. Vérifier que la ligne affiche exactement 12 points (W[current-11] … W[current])
  4. Vérifier que l'axe X affiche les labels W[n]-[y] correctement
- **Résultat attendu** :
  - Graphique : 12 points connectés, courbe fluide
  - Axe X : "W25-2024", "W26-2024", ..., "W36-2024" (si semaine courante = 36)

### Test 5.4 — Filtre catégorie (cliquer sur bouton categorie)
- **Cas** : Nominal — cliquer sur bouton "Glass" masque autres catégories, affiche Glass uniquement
- **Exécution** :
  1. Ouvrir dashboard
  2. Identifier boutons filtres catégorie (Polysilicon, Wafer, Cell, Module, Glass)
  3. Cliquer sur "Glass"
  4. Vérifier que :
     - Graphiques Polysilicon, Wafer, Cell, Module disparaissent (display:none ou opacity:0)
     - Graphique Glass reste visible
     - KPI cards : seul Glass affiché
- **Résultat attendu** :
  - Un seul graphique visible : Glass
  - Bouton "Glass" est marqué "active" (couleur, style différent)

### Test 5.5 — Date range picker (sélectionner période custom)
- **Cas** : Nominal — sélectionner date début/fin, graphiques rafraîchissent
- **Exécution** :
  1. Ouvrir dashboard
  2. Identifier date range picker (ex: input "From" et "To")
  3. Sélectionner "W20-2024" comme début et "W30-2024" comme fin
  4. Appuyer sur "Apply" ou attendre rafraîchissement auto
  5. Vérifier que graphiques affichent 10 semaines uniquement (W20…W30)
- **Résultat attendu** :
  - Graphiques : lignes réduites à 10 points (W20…W30)
  - Axes X label : "W20-2024", ..., "W30-2024"

### Test 5.6 — Hover tooltip affiche détails point
- **Cas** : Nominal — survoler un point du graphique, tooltip affiche prix exact + date
- **Exécution** :
  1. Ouvrir dashboard
  2. Survoler un point sur graphique "Polysilicon"
  3. Tooltip apparaît avec "W25-2024: 123.45 $/kg"
- **Résultat attendu** :
  - Tooltip visible à côté du curseur
  - Contient date, catégorie et prix exact (2 décimales)

### Test 5.7 — Responsive design (redimensionner fenêtre)
- **Cas** : Nominal — dashboard se redimensionne gracieusement (mobile/tablet/desktop)
- **Exécution** :
  1. Ouvrir dashboard en 1920×1080 (desktop)
  2. Vérifier que 2 graphiques par ligne
  3. Redimensionner à 768×1024 (tablet)
  4. Vérifier que 1 graphique par ligne
  5. Redimensionner à 375×667 (mobile)
  6. Vérifier que contenu reste lisible (pas de debordement horizontal)
- **Résultat attendu** :
  - Pas de scrollbar horizontal en aucune résolution
  - Texte lisible (font ≥ 12px)
  - Graphiques remplissent la largeur disponible

### Test 5.8 — Export PNG (watermark Synapsun)
- **Cas** : Limite — [SKIP] pas implémenté encore, futur Lot 2
- **Exécution** : N/A
- **Résultat attendu** : N/A

### Test 5.9 — Iframes Zoho Analytics chargent
- **Cas** : Nominal — 2 iframes Zoho (sea freight, vue 2) se chargent dans dashboard
- **Exécution** :
  1. Ouvrir `barometre-synapsun.html`
  2. Scroller jusqu'aux sections iframes Zoho
  3. Vérifier que les 2 iframes affichent du contenu (graphiques Zoho visibles)
  4. Vérifier qu'aucun message "Access denied" ou "Failed to load"
- **Résultat attendu** :
  - 2 iframes visibles avec graphiques Zoho Analytics
  - Console : zéro erreur CORS

### Test 5.10 — API XAG prix argent affiche (si présent sur dashboard)
- **Cas** : Nominal — prix argent $/oz affiché en haut du dashboard
- **Exécution** :
  1. Ouvrir `barometre-synapsun.html`
  2. Vérifier qu'un élément affiche prix argent (ex: "XAG: 32.50 $/oz")
  3. Vérifier que le prix est mis à jour via API (jeudi édition contient prix du jour)
- **Résultat attendu** :
  - Élément visible avec prix argent
  - Valeur ≥ 20 $/oz et ≤ 40 $/oz (plage normale)

---

## Composant 6 : Google Sheets Integration

**Responsabilité** : Google Sheets stocke les données, accessible en lecture publique via CSV pour dashboards, en écriture via API pour scraper.

### Test 6.1 — CSV export accessible (public URL)
- **Cas** : Nominal — URL Google Sheets CSV publique retourne 200 + CSV valide
- **Exécution** :
  1. Requête GET sur URL CSV : `https://docs.google.com/spreadsheets/d/1uZeF8NfStd_j7_rBL9pmAcT-RrOM4xQ7PE--Siekidw/gviz/tq?tqx=out:csv&sheet=taiyangnews_scrapping`
  2. Vérifier que HTTP status 200
  3. Vérifier que le corps contient en-têtes "Category | Product | Show in Barometer | W1-2024 | ..."
  4. Vérifier qu'au moins 1000 lignes (1 header + 16 catégories × 50+ produits)
- **Résultat attendu** :
  - Status 200
  - Content-Type: text/csv
  - ≥ 1000 lignes de données

### Test 6.2 — Column "Show in Barometer" respecté
- **Cas** : Nominal — produits avec "Show in Barometer" = NO ne figurent pas dans les graphiques
- **Exécution** :
  1. Manuellement dans Google Sheets, ajouter une ligne "Polysilicon | Test Poly | NO | 100 | 101 | ..."
  2. Lancer dashboard (rechargement page)
  3. Vérifier que "Test Poly" n'apparaît pas dans graphique Polysilicon
  4. Vérifier que "Test Poly" n'apparaît pas dans KPI cards
- **Résultat attendu** :
  - Dashboard : pas de point "Test Poly" sur les graphiques
  - CSV : la ligne est présente (Show in Barometer = NO)
  - Graphiques : seulement les produits avec "Show in Barometer" = YES

### Test 6.3 — Gspread authentication
- **Cas** : Nominal — Python script se connecte à Google Sheets sans erreur
- **Exécution** :
  1. Vérifier que `GOOGLE_CREDENTIALS_JSON` env var est défini (GitHub Secrets)
  2. Lancer : `python -c "from pv-price-scraper.taiyangnews_pv_scraper import get_sheet; ws = get_sheet(); print(ws.title)"`
  3. Vérifier que le script retourne "taiyangnews_scrapping"
- **Résultat attendu** :
  - stdout : "taiyangnews_scrapping"
  - Exit code : 0

### Test 6.4 — Upsert semaine nouvelle colonne
- **Cas** : Nominal — scraper crée nouvelle colonne W[N]-[Y] et l'upsert est correcte
- **Exécution** :
  1. Créer une nouvelle colonne W99-2099 vide dans Google Sheets (en-tête seulement)
  2. Lancer scraper avec --week 99 --year 2099
  3. Vérifier que la colonne W99-2099 est remplie

### Test 6.5 — Upsert semaine existante (overwrite)
- **Cas** : Nominal — scraper réécrase une colonne existante
- **Exécution** :
  1. Noter prix actuels pour W25-2024 (ex: Polysilicon = 123.45)
  2. Lancer scraper avec --week 25 --year 2024 --force
  3. Vérifier que W25-2024 est réécrit (prix peut changer)
- **Résultat attendu** :
  - Google Sheets W25-2024 : contenu remplacé (potentiellement prix différent)
  - Pas d'erreur dans les logs

---

## Composant 7 : GitHub Actions Workflows

**Responsabilité** : Orchestrer l'exécution du scraper (lundi 8h UTC) et du health check (quotidien 7h UTC).

### Test 7.1 — pv_price_weekly.yml déclenche lundi 8h UTC
- **Cas** : Nominal — workflow s'exécute automatiquement selon le schedule cron
- **Exécution** : [SKIP] — GitHub Actions timeline test (impossible en local)
- **Résultat attendu** : 
  - Vérifier dans onglet "Actions" du repo GitHub
  - Run du lundi 08:00 UTC présent dans l'historique
  - Run reçu status "completed" avec conclusion "success"

### Test 7.2 — pv_price_weekly.yml peut être déclenché manuellement
- **Cas** : Nominal — workflow "dispatch" permet un run manuel avec paramètres optionnels
- **Exécution** : [SKIP] — GitHub Actions UI test (impossible en local)
  - Aller dans onglet "Actions" → workflow "pv_price_weekly.yml"
  - Cliquer "Run workflow"
  - Vérifier que fields optionnels sont présents (--week, --year)
- **Résultat attendu** :
  - Workflow lancé après quelques secondes
  - Run visible dans historique

### Test 7.3 — health_check.yml déclenche quotidien 7h UTC
- **Cas** : Nominal — health check s'exécute chaque jour à 7h UTC
- **Exécution** : [SKIP] — GitHub Actions timeline test (impossible en local)
  - Vérifier dans onglet "Actions" du repo GitHub
  - Run quotidien 07:00 UTC présent (N jours consécutifs)
- **Résultat attendu** :
  - 7 runs en 7 jours (un par jour à 07:00 UTC)
  - Tous les runs "completed"

### Test 7.4 — health_check.yml envoie email sur échec
- **Cas** : Erreur — si health check échoue (exit 1), notification email GitHub est déclenché
- **Exécution** : [SKIP] — GitHub Actions notification test (impossible en local)
  - Provisionnement : configurer notification email sur workflow failures (GitHub repo settings)
  - Attendre un echec involontaire ou simuler (ex: bloquer l'API dans les tests)
  - Vérifier que l'email GitHub arrive
- **Résultat attendu** :
  - Email "Workflow run failed" du compte GitHub
  - Objet : "[synapsun-dev/barometer-graph-gsheet] health_check.yml failed"
  - Lien direct vers le run échoué

### Test 7.5 — Secrets GitHub sont chargés (ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_JSON)
- **Cas** : Nominal — env vars secrets sont accessibles dans le job du scraper
- **Exécution** : [SKIP] — GitHub Secrets test (impossible en local)
  - Vérifier dans repo GitHub "Settings" → "Secrets and variables" → "Actions"
  - Vérifier que ANTHROPIC_API_KEY est présent (✓ valeur non affichée)
  - Vérifier que GOOGLE_CREDENTIALS_JSON est présent (✓ valeur non affichée)
- **Résultat attendu** :
  - 2 secrets listés dans Actions secrets
  - Statut : "enabled"

### Test 7.6 — Artifact téléchargeable après chaque run
- **Cas** : Nominal — logs et rapports du scraper sont capturés comme artifact
- **Exécution** : [SKIP] — GitHub Actions artifacts test
  - Vérifier dans onglet "Actions" après un run
  - Cliquer sur le run → section "Artifacts"
  - Vérifier qu'un artifact "scraper-logs.txt" ou équivalent est présent
- **Résultat attendu** :
  - 1+ artifact téléchargeable
  - Contient les logs du scraper (timestamps, messages extractions)

---

## Composant 8 : Intégration complète (end-to-end)

**Responsabilité** : Tous les composants fonctionnent ensemble dans le flux complet lundi 8h UTC.

### Test 8.1 — Scraper → Google Sheets → Dashboard (e2e lundi 8h UTC)
- **Cas** : Nominal — flux complet de la semaine
- **Exécution** : [SKIP] — real-time test (impossible en local avant lundi)
  - Laisser tourner le scraper le lundi matin 8h UTC
  - Attendre 2 min que les données soient écrites dans Google Sheets
  - Recharger le dashboard (F5)
  - Vérifier que la semaine courante est présente dans les graphiques + KPI cards
- **Résultat attendu** :
  - Google Sheets : colonne W[current]-[year] remplie (15+ produits)
  - Dashboard : graphiques affichent le point W[current]-[year] (le plus à droite)
  - KPI cards : "last updated W[current]-[year]" visible

### Test 8.2 — Health check quotidien valide
- **Cas** : Nominal — health check tourne chaque jour et valide les 6 sources
- **Exécution** : [SKIP] — real-time test (impossible en local)
  - Vérifier les 7 derniers jours dans "Actions" → "health_check"
  - Vérifier que 7/7 runs ont status "completed" et conclusion "success"
  - Aucun email d'alerte reçu (ou "success" dans le titre)
- **Résultat attendu** :
  - 7 runs verts (✓) en 7 jours (lun … dim)

### Test 8.3 — Dashboard SEO (meta tags, Open Graph)
- **Cas** : Nominal — barometre-synapsun.html contient les meta tags pour partage social
- **Exécution** :
  1. Lire le source de barometre-synapsun.html
  2. Vérifier que `<meta name="description">` est présent
  3. Vérifier que `<meta property="og:title">` est présent
  4. Vérifier que `<meta property="og:image">` pointe vers une image existante
  5. Vérifier que `<canonical>` est présent
- **Résultat attendu** :
  - `<meta name="description" content="Baromètre Synapsun...">` présent
  - `<meta property="og:title" content="...">` présent
  - `<meta property="og:image" content="https://...">` présent
  - `<link rel="canonical" href="...">` présent

---

## PLAN D'EXÉCUTION

### Phase 1 — Tests locaux (1-2 heures)
Exécuter les tests **non-marqués [SKIP]** dans cet ordre :
1. Tests 1.1 — 1.11 (taiyangnews_pv_scraper.py) — 90 min
2. Tests 2.1 — 2.4 (backfill.py) — 30 min
3. Tests 3.1 — 3.6 (health_check.py) — 15 min
4. Tests 4.1 — 4.5 (maintenance scripts) — 20 min
5. Tests 5.1 — 5.10 (dashboards HTML) — 20 min
6. Tests 6.1 — 6.5 (Google Sheets) — 15 min

**Total Phase 1** : ~190 min (~3 heures)

### Phase 2 — Tests GitHub Actions (real-time, 1-2 semaines)
Exécuter les tests marqués [SKIP] au moment approprié :
1. Lundi 8h UTC : vérifier pv_price_weekly.yml (Test 7.1, 8.1)
2. Chaque jour : vérifier health_check.yml (Test 7.3, 8.2)
3. Mercredi : vérifier SEO meta tags (Test 8.3)

### Phase 3 — Validation finale
- Tous les tests doivent être GREEN (✓)
- Aucun test en ORANGE (⚠) ou RED (✗)
- Zéro erreurs critiques non documentées
- Projet validé PRÊT POUR PRODUCTION

---

## MATRICE D'ERREURS ET RÉSOLUTIONS

| Erreur observée | Cause probable | Résolution |
|---|---|---|
| "No products extracted" | TaiyangNews page non publiée ou structure HTML changée | Vérifier URL manuellement, adapter scraper si HTML changé |
| "Vision timeout" | API Anthropic surchargée ou réseau lent | Retry auto (3×), attendre 60s avant re-run |
| "Google Sheets auth failed" | GOOGLE_CREDENTIALS_JSON manquant/expiré | Renouveler secret Google (voir README setup) |
| "Dashboard CSV 404" | Google Sheets ID ou TAB incorrect | Vérifier SHEET_ID et SHEET_TAB dans code |
| "Zoho iframe CORS error" | Origine HTML non autorisée par Zoho | Vérifier que domain GitHub Pages est whitelisted dans Zoho settings |
| "Health check slow (>30s)" | Réseau lent ou API timeouts | Augmenter TIMEOUT dans health_check.py ou contacter ISP |
| "Dashboard graphique vide" | Pas de données pour la plage sélectionnée | Vérifier que Google Sheets a colonnes semaine requises |
| "Sticky prices" | Cache navigateur | Appuyer F5 (hard refresh) ou Ctrl+Shift+Delete (clear cache) |

---

## ARTEFACTS REQUIS

- [ ] Google Sheets publique avec ≥ 100 semaines de données
- [ ] GitHub repo avec workflows `pv_price_weekly.yml` et `health_check.yml` actifs
- [ ] Secrets GitHub : ANTHROPIC_API_KEY, GOOGLE_CREDENTIALS_JSON configurés
- [ ] Pages GitHub publique : https://synapsun-dev.github.io/barometer-graph-gsheet/
- [ ] Scripts Python : taiyangnews_pv_scraper.py, backfill.py, health_check.py, scripts maintenance

---

**Document généré** : 2026-06-18  
**Version** : 1.0  
**Statut** : ACTIF — À UTILISER POUR TOUTE VALIDATION

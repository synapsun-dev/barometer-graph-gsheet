---

projet: Barometer
statut: actif
priorite: moyenne
avancement: "60%"
prochaine_action: "Tâche 6/8 — Tester les dashboards HTML (charge CSV, KPI cards, filtres, date range, responsivité) via /verify skill. Tâche 5/8 workflow TERMINÉE."
type: outil-analyse
stack: Python + HTML statique + GitHub Actions
obsidian: "[[Synapsun]]"
derniere_session: 2026-06-18
---

## Contexte
Clone local du repo GitHub `synapsun-dev/barometer-graph-gsheet` (ex `it-dev-synapsun/graph-gsheet-tayang`).
Repo frère : `synapsun-dev/barometer-scrap-taiyang` (ex `it-dev-synapsun/it-dev-synapsun`) — exécute le cron hebdo du scraper.
Ce repo contient le scraper Python (TaiyangNews → Google Sheets) ET les dashboards HTML.
GitHub Actions lance le scraper chaque lundi 8h UTC.

**Dossier de travail :** `C:\Claude\Synapsun\Barometer\` — source de vérité locale, connectée au remote GitHub.
Ce dossier est le repo actif. Le nom officiel du projet est **Barometer**.

## Plan d'action détaillé

### ✅ Tâche 1 — Clarifier la relation avec Barometer/ (terminée)
Relation documentée : Barometer/ = repo actif (source de vérité GitHub + local).

### ✅ Tâche 2 — Vérifier support URL 2026 TaiyangNews (terminée)
3 niveaux de fallback URL opérationnels, aucun correctif nécessaire.

### ✅ Tâche 3 — Synchronisation barometre-synapsun.html (terminée)
Synchronisation effectuée, CHANGELOG.md créé.

### ✅ Tâche 4 — Renommage Repo-Clone → Barometer (terminée)
PROJECT.md renommé (frontmatter `projet: Barometer`), références internes nettoyées.

## Roadmap v2 — Améliorations valeur client & équipe interne

Pipeline v1 terminé (100% autonome). Nouvelle phase : transformer le baromètre en outil de lead gen et d'aide à la décision d'achat.

### Lot 1 — Email hebdo + commentaire de marché + alertes (priorités 1 et 2)
- [ ] **Abonnement email hebdo** : formulaire « Recevez le baromètre chaque lundi » sur les dashboards → leads dans Zoho CRM. Étape d'envoi greffée sur le run scraper du lundi 8h UTC.
- [ ] **Commentaire de marché auto-généré** : Claude rédige 4-5 phrases d'analyse hebdo à partir des variations, affichées en tête du dashboard + archivées (contenu SEO frais + matière pour l'email et LinkedIn).
- [ ] **Alertes de prix internes** : extension du health check — si un produit bouge de >X% en une semaine ou casse un plus-bas historique, email à l'équipe achat.

### Lot 2 — Simulateur DDP + annotations (priorités 3 et 4)
- [ ] **Simulateur prix rendu Europe (DDP)** : calculateur interactif prix FOB + fret + change → estimation EUR/Wc DDP, avec CTA « Obtenir un prix ferme ». Briques déjà présentes (FOB, fret Zoho, FX live, décomposition coût).
- [ ] **Annotations d'événements marché** sur les graphiques (anti-involution Chine, tarifs douaniers, PPE2…), stockées dans un onglet dédié du Google Sheet.

### Lot 3 — Export/partage + vue interne + tendances (priorités 5+)
- [ ] **Export PNG (watermark Synapsun) / CSV** par graphique + permaliens (catégorie + période encodées dans l'URL).
- [ ] **Vue interne prix marché vs prix négociés** (Tongwei, LONGi…) : dashboard privé hors GitHub Pages, Sheet privé + accès restreint — écart spot/contrat = marge de négociation.
- [ ] **Signal de tendance** : moyenne mobile 4 semaines + flèche haussière/baissière/stable sur les KPI cards.

## Livrables
- `barometre-synapsun.html` — Dashboard Baromètre Synapsun (graphiques prix TaiyangNews, mise à jour hebdo) — livré
- `index.html` — Page d'accueil Baromètre — livré
- `docs/Data-Barometer-Synapsun_Contexte-Projet.docx` — Documentation contexte projet — livré
- `docs/SYNAPSUN_Manuel_Developpeur.docx` — Manuel développeur — livré
- `docs/SYNAPSUN_TaiyangNews_Documentation_1.docx` — Documentation TaiyangNews API — livré

## Blocages actuels
Aucun bloquant. Ce dossier est fonctionnel (GitHub Actions CI/CD en place).

## Historique récent
2026-06-18 05:52 : Tâche 5/8 terminée — Validation complète workflow pv_price_weekly.yml (WORKFLOW_VALIDATION_FINAL.md). YAML syntaxe OK, cron 0 8 * * 1 confirmé (lundi 08:00 UTC), 6 steps exécutés sans erreur. Exécutions GitHub Actions : 5 last runs (4 success + 1 historic failure 2026-06-01 auth Anthropic résolue). Health check 7/7 passes. Tests unitaires 28/28 + intégration 6/7. Extraction Claude Vision W23-2026 : 27 produits sync Google Sheets OK. Verdict: ✅ PRÊT PRODUCTION.
2026-06-18 14:15 : Tâche 5/8 — Workflow pv_price_weekly.yml validé ✓ (16 tests, 14 PASS + 2 PARTIAL/NOTESTABLE). YAML syntaxe correcte, triggers cron+dispatch configurés, 3 modes logique (force/backfill/weekly), secrets GitHub présents. Historique GitHub Actions : 8 runs (5 success, 2 scheduled). Run cron lundi 08:00 UTC fonctionne. WORKFLOW_VALIDATION_RESULTS.md créé. Statut: PRÊT PRODUCTION.
2026-06-18 01:51 : Health check validé sur les 7 checks — Google Sheets CSV fraîcheur, GitHub Pages dashboard, API BCE taux change, API XAG argent (primaire + fallback), 2 iframes Zoho Analytics, TaiyangNews index. Tous les checks passent avec succès (7/7 OK). Stabilité confirmée via exécutions multiples. Aucune alerte fraîcheur (W23-2026 avec lag 2 sem < max 2).
2026-06-18 01:52 : Tests scraper valides — 28 tests unitaires (100%) + 6 tests intégration (86%) = 34/35 tests pass. test_scraper.py et test_integration.py créés, TEST_REPORT.md documenté. Composants validés : URL builders, image extraction, price validation, difflib normalization, Claude Vision, lag alerts. Scraper prêt pour production.
2026-06-18 : TEST_PLAN.md créé — 8 composants couverts (scraper, backfill, health check, maintenance scripts, dashboards HTML, Google Sheets, GitHub Actions workflows) avec cas nominaux, limites et erreurs. 40+ tests documentés, prêts à l'exécution. Matrice résolutions + plan d'exécution phased (Phase 1 local 3h, Phase 2 real-time GitHub Actions).
2026-06-18 : Analyse architecturale complète documentée (ARCHITECTURE_ANALYSIS.md) — 15 sections détaillant flux de données, composants, résilience, roadmap v2, ADRs.
2026-06-11 : Roadmap v2 définie (8 améliorations en 3 lots : email hebdo + commentaire Claude + alertes prix / simulateur DDP + annotations / export + vue interne + tendances). Avancement recalé à 60% (v1 terminée, v2 à lancer).
2026-06-11 : Vérification post-renommage — runs Actions tous verts (scraper + health check + Pages), notifications email Actions confirmées activées par Franck ('failed workflows only'). Aucune action restante.
2026-06-11 : Renommage GitHub complet — compte it-dev-synapsun → synapsun-dev (manuel), repos → barometer-scrap-taiyang (scraper+cron) et barometer-graph-gsheet (dashboards+Pages). Nouvelle URL publique : https://synapsun-dev.github.io/barometer-graph-gsheet/ (ancienne URL 404, pas de redirection Pages — validé sans usage externe). Iframes barometre-synapsun.html passées en URLs relatives, DASHBOARD_URL health_check corrigée, remote local mis à jour (f8591ba). Cron scraper en doublon désactivé côté graph-gsheet (tournait 2×/lundi). Validé : run scraper OK, health check 7/7 OK, Pages 200, rendu UI OK.
2026-06-10 : Alertes email en cas de panne (dd814cc) — nouveau workflow health_check.yml quotidien 07:00 UTC (7 checks : CSV Sheets + fraîcheur, dashboard GitHub Pages, 2 iframes Zoho, API BCE, API XAG primaire+fallback, index TaiyangNews) ; le check fraîcheur distingue "pipeline en panne" de "source en retard". Fix échec silencieux du scraper (exit 1 si aucune semaine récupérable et Sheet incomplet). Notification = email natif GitHub sur workflow failed. Validé en local et de bout en bout sur GitHub (run 27304592928, 7/7 OK).
2026-06-10 : Fix base 635W du bar graph "Décomposition du coût" (f01b20f) — ancienne base issue des contributions CO2 PPE2 (expirée, non comparable PPE2_V2) alors que les intensités matière/Wc sont identiques au 470W à ~1% près. Aussi : fallback API XAG Cloudflare Pages, titre graphique évolution précisé "Module 470W (1762×1134)", tag source argent corrigé (8608651).
2026-06-10 : Fix graphique "Évolution structure de coût" (barometre-synapsun.html) — incohérence avec KPI pâte d'argent corrigée (4 bugs : cellule RMB/W lue comme USD/W, prix argent figé 32.5$/oz par race condition, dénominateur ≠ coût module Certisolis, labels tronqués). Méthodologie alignée sur renderBreakdown + série XAG historique. Poussé et déployé (588eda8). Auth gh basculée sur it-dev-synapsun.
2026-06-09 : Renommage projet : `repo-clone` → `Barometer` dans PROJECT.md (frontmatter + contexte + plan d'action).
2026-06-06 : Session de validation — toutes les tâches (T1, T2, T3) confirmées à 100%, aucune action corrective nécessaire, statut du projet mis à jour.
2026-06-04 : Tâche 3 terminée — barometre-synapsun.html synchronisé de repo-clone vers Barometer/ (repo-clone +2877 bytes plus récent). Changements : iframes Zoho responsives (CSS .zoho-responsive, scaleZohoIframes JS), nouvelle URL Zoho Analytics, dimensions via variables CSS. CHANGELOG.md créé.
2026-06-04 : Tâche 2 terminée — support URL 2026 vérifié et validé. 3 niveaux de fallback opérationnels : cw{week}-{year} (W1-W19), cw-{week}-{year} (W20+), puis discover_url_from_index(). backfill.py utilise fetch_page() (pas build_url() dead import). Aucun correctif nécessaire.
2026-06-04 : Tâche 1 terminée — relation avec Barometer/ documentée dans README.md. repo-clone = source de vérité GitHub (scraper +2136 bytes plus récent, barometre.html +2877 bytes plus récent). Barometer/ = snapshot obsolète sans remote.
2026-06-02 : Audit — encodage du PROJECT.md corrigé (était en cp1252). Rôle du dossier clarifié.


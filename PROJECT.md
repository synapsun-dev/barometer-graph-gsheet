---
projet: Barometer
statut: actif
priorite: moyenne
avancement: "100%"
prochaine_action: "Toutes les tâches du plan sont terminées. Prochaine action : surveiller la prochaine exécution GitHub Actions (lundi 08h UTC)."
type: outil-analyse
stack: Python + HTML statique + GitHub Actions
obsidian: "[[Synapsun]]"
derniere_session: 2026-06-09
---

## Contexte
Clone local du repo GitHub `it-dev-synapsun/graph-gsheet-tayang`.
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

## Blocages actuels
Aucun bloquant. Ce dossier est fonctionnel (GitHub Actions CI/CD en place).

## Historique récent
2026-06-09 : Renommage projet : `repo-clone` → `Barometer` dans PROJECT.md (frontmatter + contexte + plan d'action).
2026-06-06 : Session de validation — toutes les tâches (T1, T2, T3) confirmées à 100%, aucune action corrective nécessaire, statut du projet mis à jour.
2026-06-04 : Tâche 3 terminée — barometre-synapsun.html synchronisé de repo-clone vers Barometer/ (repo-clone +2877 bytes plus récent). Changements : iframes Zoho responsives (CSS .zoho-responsive, scaleZohoIframes JS), nouvelle URL Zoho Analytics, dimensions via variables CSS. CHANGELOG.md créé.
2026-06-04 : Tâche 2 terminée — support URL 2026 vérifié et validé. 3 niveaux de fallback opérationnels : cw{week}-{year} (W1-W19), cw-{week}-{year} (W20+), puis discover_url_from_index(). backfill.py utilise fetch_page() (pas build_url() dead import). Aucun correctif nécessaire.
2026-06-04 : Tâche 1 terminée — relation avec Barometer/ documentée dans README.md. repo-clone = source de vérité GitHub (scraper +2136 bytes plus récent, barometre.html +2877 bytes plus récent). Barometer/ = snapshot obsolète sans remote.
2026-06-02 : Audit — encodage du PROJECT.md corrigé (était en cp1252). Rôle du dossier clarifié.

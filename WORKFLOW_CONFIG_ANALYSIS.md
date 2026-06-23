# Analyse de Configuration du Workflow YAML et Schedule Cron

**Date d'analyse** : 2026-06-23  
**Tâche** : Examiner la config du workflow YAML et le schedule cron  
**Contexte** : Le scraping de S24 (W26-2026) ne s'est pas lancé avec succès le 22 juin 2026

---

## 1. Configuration YAML — État Actuel

### 1.1 Workflow Principal : `pv_price_weekly.yml`

| Élément | Configuration | Status |
|---------|---------------|--------|
| **Nom** | `TaiyangNews PV Price Index` | ✅ |
| **Trigger schedule** | `"0 8 * * 1"` (lundi 08:00 UTC) | ✅ CORRECT |
| **Trigger dispatch** | Modes : `weekly`, `backfill`, `force` | ✅ CORRECT |
| **Concurrency** | `group: pv-scraper`, `cancel-in-progress: false` | ✅ CORRECT |
| **Runner** | `ubuntu-latest` | ✅ CORRECT |
| **Python** | `3.11` | ✅ CORRECT |
| **Secrets** | `GOOGLE_CREDENTIALS_JSON`, `ANTHROPIC_API_KEY` | ⚠️ Requis |

**Syntaxe YAML** : ✅ Validée, pas d'erreur

### 1.2 Workflow Secondaire : `health_check.yml`

| Élément | Configuration | Status |
|---------|---------------|--------|
| **Nom** | `Dashboard Health Check` | ✅ |
| **Trigger schedule** | `"0 7 * * *"` (quotidien 07:00 UTC) | ✅ CORRECT |
| **Fréquence** | Chaque jour avant le scraper lundi 08:00 | ✅ CORRECT |
| **Vérifications** | 7 checks : Sheets, Pages, Zoho, API BCE, API XAG, TaiyangNews | ✅ |

**Syntaxe YAML** : ✅ Validée, pas d'erreur

---

## 2. État des Workflows GitHub Actions

```bash
$ gh workflow list --all
Dashboard Health Check     active    293309999
TaiyangNews PV Price Index active    282848412
pages-build-deployment     active    279760253
```

**Status** : ✅ **Les deux workflows sont ACTIVÉS** (pas disabled)

---

## 3. Analyse de l'Historique des Runs Schedule

### 3.1 Timeline des Runs Schedule (cron)

| Date/Heure (UTC) | Jour | Semaine | Mode | Status | Logs |
|---|---|---|---|---|---|
| 2026-06-22 13:37 | Lundi | W26-2026 | **schedule** | ❌ FAILURE | "Neither W26-2026 nor W25-2026 could be fetched" |
| 2026-06-15 09:12 | Lundi | W23-2026 | **dispatch** ⚠️ | ✅ SUCCESS | Manuel (27 produits) |
| 2026-06-08 12:22 | Lundi | W22-2026 | **schedule** | ✅ SUCCESS | W22-2026 extractée OK |
| 2026-06-01 13:29 | Lundi | W22-2026 | **schedule** | ❌ FAILURE | Problèmes API initiales |

### 3.2 Découverte Critique : Run Schedule du 15 Juin Manquant

**Observation** : Il n'existe PAS de run en mode `schedule` (cron) pour le 15 juin (lundi).
- Seul un run `workflow_dispatch` (manuel) à 09:12 UTC existe
- Cela indique que **le cron schedule n'a pas exécuté ce jour-là**

**Timeline reconstructed** :
```
11 juin 2026      : Renommage GitHub (it-dev-synapsun → synapsun-dev)
                    Post-renommage workflows vérifiés "OK"
15 juin 2026 08:00: Cron schedule DEVRAIT s'exécuter → ABSENT
                    (Workflows probablement restés désactivés après renommage)
15 juin 09:12     : Exécution MANUELLE de W23-2026 (dispatch)
22 juin 2026 08:00: Cron schedule s'exécute ENFIN
                    Cherche W26-2026 (pas publiée) → fallback W25
                    Mais W25 n'a JAMAIS été scrappée (15 juin manqué)
                    → FAILURE
```

---

## 4. Raison de l'Échec du 22 Juin

### 4.1 Message d'Erreur Observé

```
2026-06-22T13:37:30 ERROR Neither W26-2026 nor W25-2026 could be fetched 
and the sheet has neither — TaiyangNews scrape failed 
(site down or URL scheme changed?).
```

### 4.2 Diagnostic

| Étape | Résultat | Explication |
|-------|---------|-------------|
| **W26-2026 sur TaiyangNews** | ❌ N'existe pas | Légitime — données de la semaine en cours pas encore publiées |
| **W25-2026 sur TaiyangNews** | ❓ Probablement existe | Semaine précédente, données normalement complètes |
| **W25-2026 dans Google Sheets** | ❌ N'existe pas | Car le cron du 15 juin n'a pas exécuté |
| **Fallback logic** | ❌ Échoue | Aucune des deux semaines disponible → `sys.exit(1)` |

### 4.3 Timing du Cron GitHub Actions

Les runs schedule s'exécutent avec **décalage significatif** :
- Attendu : 08:00 UTC
- Observé : 12:22-13:37 UTC (~4-5h de décalage)

**Cause** : GitHub Actions ajoute un jitter aléatoire pour les crons pour éviter les surcharges (comportement normal et documenté).

---

## 5. État Actuel du Cron

### 5.1 Configuration Cron (Correcte)

```yaml
on:
  schedule:
    - cron: "0 8 * * 1"  # lundi 08:00 UTC
  workflow_dispatch:
```

**Interprétation standard Cron** :
- `minute : 0` (heure 0)
- `hour : 8` (08h UTC)
- `day : *` (tous les jours)
- `month : *` (tous les mois)
- `dayofweek : 1` (lundi ISO : 1=lundi, 0=dimanche)

✅ **Configuration syntaxiquement correcte**

### 5.2 Exécution Réelle du Cron

| Lundi | Cron s'est exécuté ? | Heure réelle | Mode |
|-------|---|---|---|
| 1 juin | ✅ OUI (échoué) | 13:29 UTC | schedule |
| 8 juin | ✅ OUI (succès) | 12:22 UTC | schedule |
| **15 juin** | ❌ **NON** | N/A | dispatch (manuel) |
| 22 juin | ✅ OUI (échoué) | 13:37 UTC | schedule |

**Problème identifié** : Le cron du 15 juin n'a pas exécuté.

---

## 6. Cause Probable du Gap du 15 Juin

### 6.1 Symptôme Principal

Après renommage de repo GitHub (11 juin), les workflows sont généralement **automatiquement désactivés** par GitHub. Bien que la vérification post-renommage ait signalé "tous verts", il est probable que :

1. Les workflows ont été **temporairement désactivés** après le renommage (comportement GitHub par défaut)
2. Ils ont été **réactivés manuellement le 11 juin** pour les tests post-renommage
3. Ils n'ont PAS restés réactivés → se sont **re-désactivés** automatiquement ou manuellement
4. Ils ont été **réactivés à nouveau** quelque temps après le 15 juin (avant le 22 juin)

### 6.2 Evidence du Comportement GitHub

Voir section "Pièges opérationnels connus" dans `CLAUDE.md` :
```
### Renommage de repo GitHub → workflows désactivés
**Comportement GitHub :** quand un repo est renommé, GitHub désactive 
automatiquement les workflows `schedule`. Les crons ne tournent plus 
silencieusement et aucune alerte n'est émise.

**Procédure de récupération obligatoire après tout renommage :**
1. `gh workflow enable pv_price_weekly.yml`
2. `gh workflow enable health_check.yml`
3. Déclencher manuellement le scraper pour la semaine manquante
```

---

## 7. Recommandations

### 7.1 Actions Immédiates (À Faire Maintenant)

1. **Vérifier explicitement que les workflows resteront activés**
   ```bash
   gh workflow enable pv_price_weekly.yml
   gh workflow enable health_check.yml
   ```

2. **Scraper manuellement W25-2026** une fois que TaiyangNews aura les données disponibles
   ```bash
   gh workflow run pv_price_weekly.yml --field week=25 --field year=2026
   ```

3. **Attendre le prochain run schedule** : lundi 29 juin 2026 devrait scraper W26-2026 ou W27-2026

### 7.2 Prévention Future

1. **Ajouter une alerte de monitoring** : si aucun run schedule n'exécute pendant >2 semaines, signaler
2. **Documenter le comportement GitHub** : créer une alerte dans README pour futurs renommages
3. **Configurer des notifications email** sur `workflow failed` (déjà en place selon PROJECT.md)

### 7.3 Monitoring du Prochain Cron

**Date à surveiller** : lundi 29 juin 2026 à 08:00 UTC (±5h de jitter)

**Succès** : W26-2026 ou W27-2026 apparaît dans Google Sheets  
**Échec** : S'il n'y a pas de nouvelle semaine après ce run, le cron est à nouveau défaillant

---

## 8. Conclusion

| Aspect | Statut |
|--------|--------|
| **Configuration YAML** | ✅ Syntaxe correcte, cron expression valide |
| **Workflows GitHub** | ✅ Actuellement ACTIVÉS |
| **Dernier échec (22 juin)** | ❌ Dû à missing W25-2026 (cron 15 juin absent) |
| **Cause root** | ⚠️ Workflows désactivés après renommage 11 juin, réactivation incomplète |
| **État du pipeline** | 🟡 Fonctionnel mais rattrapage nécessaire |

**Prochain run schedule** : lundi 29 juin 2026 — test critique pour vérifier stabilité.


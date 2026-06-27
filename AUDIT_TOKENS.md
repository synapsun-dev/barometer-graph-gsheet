## [TOKENS] Audit des Tokens
**Risk Score** : 0.45/1.0

### Findings
1. **[MEDIUM]** Usage récent: 278,182 tokens (5h) / 10,881,924 tokens (semaine) / 1,985,385 tokens (aujourd'hui)
   >> Remediation: Si usage > 80% de limite : découper les tâches ou utiliser caching/cache_read
2. **[INFO]** Aucun TOKEN_LIMIT détecté — usage nominal
3. **[HIGH]** Croissance rapide : +245% en 2 semaines
   >> Remediation: Si croissance > 50% : analyser les nouvelles tâches et optimiser les patterns
4. **[MEDIUM]** ⚠️ Limites locales désactivées (session_limit=0 ou weekly_limit=0)
   >> Remediation: Recalibrer les limites selon le plan d'abonnement Claude (Pro/Max5x/Max20x), ou maintenir désactivées si inexactes

### Recommendations
- **[HIGH]** Optimiser l'usage de tokens — Découper les tâches, utiliser le cache, améliorer les prompts

## JSON Result

```json
{
  "findings": [
    {
      "type": "token_usage_recent",
      "severity": "MEDIUM",
      "description": "Usage récent: 278,182 tokens (5h) / 10,881,924 tokens (semaine) / 1,985,385 tokens (aujourd'hui)",
      "details": {
        "last_5h_output": 278182,
        "weekly_output": 10881924,
        "today_output": 1985385,
        "events_scanned": 12171
      },
      "remediation": "Si usage > 80% de limite : découper les tâches ou utiliser caching/cache_read"
    },
    {
      "type": "token_limit_check",
      "severity": "INFO",
      "description": "Aucun TOKEN_LIMIT détecté — usage nominal"
    },
    {
      "type": "usage_trend",
      "severity": "HIGH",
      "description": "Croissance rapide : +245% en 2 semaines",
      "details": {
        "recent_2w_avg": 2290352,
        "growth_pct": 245.0,
        "history_weeks": 8
      },
      "remediation": "Si croissance > 50% : analyser les nouvelles tâches et optimiser les patterns"
    },
    {
      "type": "limits_disabled",
      "severity": "MEDIUM",
      "description": "⚠️ Limites locales désactivées (session_limit=0 ou weekly_limit=0)",
      "details": {
        "session_limit": 0,
        "weekly_limit": 0
      },
      "remediation": "Recalibrer les limites selon le plan d'abonnement Claude (Pro/Max5x/Max20x), ou maintenir désactivées si inexactes"
    }
  ],
  "risk_score": 0.45,
  "recommendations": [
    {
      "priority": "HIGH",
      "action": "Optimiser l'usage de tokens",
      "details": "Découper les tâches, utiliser le cache, améliorer les prompts"
    }
  ]
}
```

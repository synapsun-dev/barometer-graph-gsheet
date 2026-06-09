# CHANGELOG — Synapsun Barometer

## [2026-06-01] — v2026-06-01c — Iframes Zoho responsives

**Fichier modifié :** `barometre-synapsun.html`  
**Source :** `repo-clone/` → synchronisé vers `Barometer/` le 2026-06-04

### Modifications apportées

#### 1. CSS `.ifr-wrap` — refonte complète pour responsive

**Avant (2 lignes) :**
```css
.ifr-wrap{border-radius:var(--r);overflow:hidden;box-shadow:var(--sh);background:#fff}
.ifr-wrap iframe{display:block;width:100%;height:100%;border:none}
```

**Après :** CSS étendu avec :
- Nouvelle classe `.zoho-responsive` utilisant `aspect-ratio`, `container-type:inline-size`
- Variables CSS `--iframe-w`, `--iframe-h`, `--scale-w`, `--scale-h` pour le dimensionnement
- Masquage des scrollbars (`scrollbar-width:none`, `::-webkit-scrollbar{display:none}`)
- Positionnement absolu de l'iframe pour permettre le `transform:scale()`

#### 2. URL Zoho Analytics — premier bloc mis à jour

| | Valeur |
|---|---|
| **Ancienne URL** | `analytics.zoho.com/open-view/1373627000026674003` |
| **Nouvelle URL** | `analytics.zoho.com/open-view/1373627000027120086/d6435972...` |
| **Dimensions** | `700×800px` fixe → `--iframe-w:800;--iframe-h:600;--scale-w:499;--scale-h:480` |

#### 3. Second iframe Zoho — passage en responsive

| | Ancienne valeur | Nouvelle valeur |
|---|---|---|
| Classe | `ifr-wrap` | `ifr-wrap zoho-responsive` |
| Dimensions | `height:500px;width:800px` | `--iframe-w:800;--iframe-h:900;--scale-w:800;--scale-h:830` |
| Attribut | `frameborder="0"` | `scrolling="no"` |

#### 4. JavaScript — fonction `scaleZohoIframes()` ajoutée

Nouvelle fonction et écouteurs d'événements :
- `scaleZohoIframes()` : calcule le ratio `containerWidth / --scale-w` et applique `transform:scale()`
- Écouteurs sur `load` et `resize` pour recalculer à chaque redimensionnement
- Écouteur `postMessage` : si Zoho Analytics envoie la hauteur du chart, met à jour `--scale-h` automatiquement et relance le scale

---

## Historique des synchronisations

| Date | Direction | Motif |
|---|---|---|
| 2026-06-04 | `repo-clone/` → `Barometer/` | Synchro initiale — repo-clone en avance de +2877 bytes (iframes responsives) |

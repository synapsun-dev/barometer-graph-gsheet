"""Cache des graphiques Zoho Analytics (fret maritime, DDP Europe).

Les vues publiques `open-view` de Zoho renvoient une image PNG régénérée à
chaque appel, en 30 s à plus de 2 min (mesuré le 2026-11-23) : en iframe, la
page restait vide ou très lente. Ce script télécharge les PNG côté serveur
(GitHub Actions) et les dépose dans data/zoho/, servis ensuite par GitHub Pages
via une simple <img>.

Règles :
- un PNG n'est remplacé que s'il est valide (signature, dimensions IHDR, taille) ;
  en cas d'échec Zoho, l'image précédente reste en ligne ;
- data/zoho/meta.json garde la date du dernier téléchargement réussi
  (réécrite si l'image change ou si la date a plus de META_REFRESH_DAYS jours,
  pour éviter un commit quotidien sans changement) ;
- exit(1) seulement si une image en cache a plus de MAX_AGE_DAYS jours
  (un échec ponctuel de Zoho ne déclenche pas d'alerte).

Usage : python pv-price-scraper/fetch_zoho_charts.py
"""
import hashlib
import json
import struct
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "zoho"
META_PATH = OUT_DIR / "meta.json"

CHARTS = {
    "sea_freight": "https://analytics.zoho.com/open-view/1373627000027120086/"
                   "d6435972ee5651e23d81649703e4b2320b5f037c5a75c8bb38c908c5e858f431",
    "ddp_europe": "https://analytics.zoho.com/open-view/1373627000030138796",
}

TIMEOUT = 300          # Zoho peut dépasser 2 min
RETRIES = 3
RETRY_DELAY = 30
MIN_BYTES = 10_000
MAX_AGE_DAYS = 8
META_REFRESH_DAYS = 3
KNOWN_VARIANTS = 4     # empreintes des dernières variantes de rendu Zoho mémorisées
PNG_SIG = b"\x89PNG\r\n\x1a\n"
FMT = "%Y-%m-%dT%H:%M:%SZ"


def png_size(data: bytes) -> tuple[int, int]:
    """Renvoie (largeur, hauteur) lues dans le bloc IHDR, ou lève ValueError."""
    if len(data) < 24 or data[:8] != PNG_SIG or data[12:16] != b"IHDR":
        raise ValueError("pas un PNG")
    return struct.unpack(">II", data[16:24])


def fetch(key: str, url: str) -> bytes | None:
    """Télécharge et valide un PNG ; None après RETRIES échecs."""
    for attempt in range(1, RETRIES + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
            w, h = png_size(data)
            if len(data) < MIN_BYTES:
                raise ValueError(f"trop petit ({len(data)} octets)")
            print(f"[{key}] OK {w}x{h}, {len(data)} octets, {time.time() - t0:.0f} s")
            return data
        except Exception as exc:  # réseau, timeout, contenu invalide
            print(f"[{key}] tentative {attempt}/{RETRIES} échouée ({time.time() - t0:.0f} s) : {exc}")
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
    return None


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}
    now = datetime.now(timezone.utc)

    with ThreadPoolExecutor(len(CHARTS)) as pool:
        results = dict(zip(CHARTS, pool.map(lambda kv: fetch(*kv), CHARTS.items())))

    meta_changed = False
    stale = []
    for key, data in results.items():
        path = OUT_DIR / f"{key}.png"
        entry = meta.get(key, {})
        if data is not None:
            # Zoho a plusieurs serveurs de rendu : à données égales, l'image peut
            # différer d'un pixel (constaté 2026-11-23 sur le fret, 2 variantes).
            # Une variante déjà vue n'est donc pas une mise à jour.
            digest = hashlib.sha256(data).hexdigest()
            known = entry.get("known_sha256", [])
            changed = not path.exists() or (digest not in known and path.read_bytes() != data)
            if changed:
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(data)
                tmp.replace(path)
            last = entry.get("fetched_at")
            old = not last or (now - datetime.strptime(last, FMT).replace(tzinfo=timezone.utc)).days >= META_REFRESH_DAYS
            if changed or old or digest not in known:
                w, h = png_size(data)
                known = ([digest] + [k for k in known if k != digest])[:KNOWN_VARIANTS]
                meta[key] = {"fetched_at": now.strftime(FMT), "width": w, "height": h,
                             "source": CHARTS[key], "known_sha256": known}
                meta_changed = True
            print(f"[{key}] image {'mise à jour' if changed else 'inchangée'}")
        else:
            last = entry.get("fetched_at")
            age = (now - datetime.strptime(last, FMT).replace(tzinfo=timezone.utc)).days if last else None
            print(f"[{key}] échec Zoho — image en cache conservée (âge : {age} j)")
            if age is None or age > MAX_AGE_DAYS:
                stale.append(f"{key} ({'jamais téléchargé' if age is None else f'{age} jours'})")

    if meta_changed:
        META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if stale:
        print(f"ERROR: cache Zoho périmé (> {MAX_AGE_DAYS} j) : {', '.join(stale)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Rendu mensuel du baromètre — image + PDF pour la page /barometre de synapsun.com
---------------------------------------------------------------------------------
Capture le dashboard public (GitHub Pages) en headless Chromium (Playwright) et
produit les deux fichiers attendus par l'admin EasyAdmin du portail (entité
`Barometer`, rôle ROLE_BAROMETER) :

  - image  ≤ 2 Mo  (contrainte Assert\\Image maxSize 2048k)
  - PDF    ≤ 4 Mo  (contrainte Assert\\File  maxSize 4096k)
  - meta.txt : meta title / description / keywords proposés pour la période

Sortie : snapshots/{YYYY-MM}/barometre-{YYYY-MM}.{png|jpg,pdf} + meta.txt
L'upload dans EasyAdmin reste un geste humain (validation éditoriale).

Usage :
    pip install playwright && playwright install chromium
    python render_snapshot.py [--url URL] [--outdir DIR] [--period YYYY-MM]
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_URL = "https://synapsun-dev.github.io/barometer-graph-gsheet/barometre-synapsun.html"
DEFAULT_OUTDIR = Path(__file__).resolve().parent.parent / "snapshots"

MAX_IMAGE_BYTES = 2048 * 1024   # limite VichUploader image du portail
MAX_PDF_BYTES   = 4096 * 1024   # limite VichUploader PDF du portail

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]


def build_meta(period: str) -> str:
    """Meta title/description/keywords proposés pour l'entité Barometer."""
    year, month = period.split("-")
    mois = MOIS_FR[int(month) - 1]
    title = f"Baromètre des prix modules photovoltaïques — {mois} {year} | Synapsun"
    description = (
        f"Baromètre Synapsun {mois} {year} : suivi hebdomadaire des prix de la filière "
        "photovoltaïque — polysilicium, wafers, cellules TOPCon, modules FOB Chine, "
        "verre solaire, fret maritime et taux de change EUR/USD/CNY."
    )
    keywords = (
        "prix modules photovoltaïques, baromètre PV, prix polysilicium, prix wafer, "
        f"modules TOPCon, FOB Chine, {mois} {year}, Synapsun"
    )
    return (
        f"metaTitle: {title}\n"
        f"metaDescription: {description}\n"
        f"metaKeywords: {keywords}\n"
        f"date (période): {year}-{month}-01\n"
    )


def render(url: str, outdir: Path, period: str) -> list[Path]:
    """Capture le dashboard → [image, pdf, meta.txt] dans outdir/period/."""
    target = outdir / period
    target.mkdir(parents=True, exist_ok=True)
    produced: list[Path] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 1000},
                                device_scale_factor=1.5)
        logger.info("Chargement de %s …", url)
        page.goto(url, wait_until="networkidle", timeout=90_000)
        # Attendre les graphiques Chart.js (données CSV/JSON chargées en async)
        page.wait_for_selector("#chart-cost-evolution", timeout=30_000)
        page.wait_for_timeout(8_000)  # fin des animations + iframes

        # ── Image : PNG, puis JPEG qualité décroissante si > 2 Mo ──
        png_path = target / f"barometre-{period}.png"
        page.screenshot(path=str(png_path), full_page=True)
        img_path = png_path
        if png_path.stat().st_size > MAX_IMAGE_BYTES:
            logger.info("PNG %.0f Ko > 2 Mo — conversion JPEG",
                        png_path.stat().st_size / 1024)
            png_path.unlink()
            for quality in (85, 70, 55):
                jpg_path = target / f"barometre-{period}.jpg"
                page.screenshot(path=str(jpg_path), full_page=True,
                                type="jpeg", quality=quality)
                img_path = jpg_path
                if jpg_path.stat().st_size <= MAX_IMAGE_BYTES:
                    break
        size = img_path.stat().st_size
        logger.info("Image : %s (%.0f Ko)", img_path.name, size / 1024)
        if size > MAX_IMAGE_BYTES:
            logger.warning("Image toujours > 2 Mo — l'upload EasyAdmin sera refusé")
        produced.append(img_path)

        # ── PDF (rendu print Chromium) ──
        pdf_path = target / f"barometre-{period}.pdf"
        page.emulate_media(media="print")
        page.pdf(path=str(pdf_path), format="A4", print_background=True,
                 scale=0.7, margin={"top": "10mm", "bottom": "10mm",
                                    "left": "8mm", "right": "8mm"})
        size = pdf_path.stat().st_size
        logger.info("PDF : %s (%.0f Ko)", pdf_path.name, size / 1024)
        if size > MAX_PDF_BYTES:
            logger.warning("PDF > 4 Mo — l'upload EasyAdmin sera refusé")
        produced.append(pdf_path)

        browser.close()

    meta_path = target / "meta.txt"
    meta_path.write_text(build_meta(period), encoding="utf-8")
    produced.append(meta_path)
    return produced


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot mensuel image+PDF du baromètre")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--period", default=date.today().strftime("%Y-%m"),
                        help="Période YYYY-MM (défaut : mois courant)")
    args = parser.parse_args()

    files = render(args.url, args.outdir, args.period)
    logger.info("Snapshot %s terminé : %s", args.period,
                ", ".join(f.name for f in files))
    return 0


if __name__ == "__main__":
    sys.exit(main())

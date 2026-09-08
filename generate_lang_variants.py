#!/usr/bin/env python3
"""
Génère les 4 variantes linguistiques du baromètre (EN/DE/IT/ES) à partir du
fichier maître barometre-synapsun.html (FR).

Le corps HTML, le CSS et le script JS sont strictement identiques dans les 5
fichiers (le rendu textuel est piloté à 100% par data-i18n / STRINGS[lang] au
chargement, cf. detectLang() + initLang() dans barometre-synapsun.html) :
seul le <head> (SEO : title, meta, OG, Twitter, JSON-LD, hreflang) et
l'attribut <html lang="..."> diffèrent d'un fichier à l'autre.

Usage :
    python generate_lang_variants.py

Ne JAMAIS éditer barometre-synapsun-{en,de,it,es}.html à la main : éditer
barometre-synapsun.html (le corps/JS partagé, ou la section HEADS ci-dessous
pour le SEO) puis relancer ce script.
"""
import re
from pathlib import Path

MASTER = Path(__file__).parent / "barometre-synapsun.html"

BANNER = (
    "<!-- GÉNÉRÉ AUTOMATIQUEMENT depuis barometre-synapsun.html "
    "par generate_lang_variants.py — NE PAS ÉDITER À LA MAIN. -->\n"
)

# hreflang / og:locale:alternate communs à réinjecter tels quels (identiques
# dans les 5 fichiers, cf. barometre-synapsun.html) — on ne les recalcule pas
# ici, on réutilise le bloc du master.

HEADS = {
    "en": {
        "title": "PV Module Price Barometer 2025 | Synapsun",
        "description": "Weekly tracking of PV module prices: polysilicon, wafers, TOPCon & Back Contact cells, FOB China prices, sea freight, exchange rates and DDP Europe prices. By Synapsun, PV module expert.",
        "keywords": "PV module prices, PV price barometer, polysilicon price, solar wafer price, TOPCon module price, back contact module price, solar panel price 2025, FOB China PV modules, solar sea freight, EUR USD CNY exchange rate, Synapsun",
        "canonical": "https://synapsun.com/barometer",
        "og_title": "PV Module Price Barometer | Synapsun",
        "og_description": "Weekly PV module price tracking from raw material to module delivered in Europe. TOPCon, Back Contact, FOB China, freight, exchange rates.",
        "og_locale": "en_GB",
        "twitter_title": "PV Module Price Barometer | Synapsun",
        "twitter_description": "Weekly PV price tracking: polysilicon, wafers, TOPCon & Back Contact modules, sea freight and exchange rates.",
        "ld_name": "PV Module Price Barometer",
        "ld_description": "Weekly time series of PV supply chain prices: polysilicon, wafers, cells, modules, sea freight and EUR/USD/CNY exchange rates.",
        "ld_inLanguage": "en-GB",
        "breadcrumb_home": "Home",
        "breadcrumb_modules": "PV Modules",
        "breadcrumb_modules_url": "https://synapsun.com/en/pv-modules",
        "breadcrumb_barometer": "Price Barometer",
        "dataset_name": "Synapsun Barometer — PV Module Prices",
        "dataset_description": "Weekly time series of PV supply chain component prices: polysilicon, wafers, cells, modules, sea freight and EUR/USD/CNY exchange rates.",
        "license": "https://synapsun.com/en/legal-notice",
        "keywords_list": '["photovoltaic", "solar modules", "polysilicon price", "TOPCon", "Back Contact", "sea freight", "exchange rate"]',
        "variable_measured": [
            "Polysilicon price (RMB/kg)",
            "Wafer prices (USD/W)",
            "Cell prices (RMB/W)",
            "FOB China module prices (USD/Wp)",
            "Shanghai-Europe sea freight (USD/40HC)",
            "EUR/USD rate",
            "EUR/CNY rate",
            "DDP Europe module prices (EUR/Wp)",
        ],
    },
    "de": {
        "title": "Preisbarometer für PV-Module 2025 | Synapsun",
        "description": "Wöchentliche Verfolgung der PV-Modulpreise: Polysilizium, Wafer, TOPCon- & Back-Contact-Zellen, FOB-Preise China, Seefracht, Wechselkurse und DDP-Preise Europa. Von Synapsun, PV-Modul-Experte.",
        "keywords": "PV-Modulpreise, PV-Preisbarometer, Polysiliziumpreis, Solarwaferpreis, TOPCon-Modulpreis, Back-Contact-Modulpreis, Solarmodulpreis 2025, FOB China PV-Module, Solar-Seefracht, EUR USD CNY Wechselkurs, Synapsun",
        "canonical": "https://synapsun.com/de/barometer",
        "og_title": "Preisbarometer für PV-Module | Synapsun",
        "og_description": "Wöchentliche Verfolgung der PV-Modulpreise vom Rohstoff bis zum in Europa gelieferten Modul. TOPCon, Back Contact, FOB China, Fracht, Wechselkurse.",
        "og_locale": "de_DE",
        "twitter_title": "Preisbarometer für PV-Module | Synapsun",
        "twitter_description": "Wöchentliche PV-Preisverfolgung: Polysilizium, Wafer, TOPCon- & Back-Contact-Module, Seefracht und Wechselkurse.",
        "ld_name": "Preisbarometer für PV-Module",
        "ld_description": "Wöchentliche Zeitreihen der Preise entlang der PV-Wertschöpfungskette: Polysilizium, Wafer, Zellen, Module, Seefracht und EUR/USD/CNY-Wechselkurse.",
        "ld_inLanguage": "de-DE",
        "breadcrumb_home": "Startseite",
        "breadcrumb_modules": "PV-Module",
        "breadcrumb_modules_url": "https://synapsun.com/de/pv-module",
        "breadcrumb_barometer": "Preisbarometer",
        "dataset_name": "Synapsun-Barometer — Preise für PV-Module",
        "dataset_description": "Wöchentliche Zeitreihen der Preise entlang der PV-Wertschöpfungskette: Polysilizium, Wafer, Zellen, Module, Seefracht und EUR/USD/CNY-Wechselkurse.",
        "license": "https://synapsun.com/de/impressum",
        "keywords_list": '["Photovoltaik", "Solarmodule", "Polysiliziumpreis", "TOPCon", "Back Contact", "Seefracht", "Wechselkurs"]',
        "variable_measured": [
            "Polysiliziumpreis (RMB/kg)",
            "Waferpreise (USD/W)",
            "Zellpreise (RMB/W)",
            "FOB-Modulpreise China (USD/Wp)",
            "Seefracht Shanghai-Europa (USD/40HC)",
            "Wechselkurs EUR/USD",
            "Wechselkurs EUR/CNY",
            "DDP-Modulpreise Europa (EUR/Wp)",
        ],
    },
    "it": {
        "title": "Barometro dei prezzi dei moduli fotovoltaici 2025 | Synapsun",
        "description": "Monitoraggio settimanale dei prezzi dei moduli fotovoltaici: polisilicio, wafer, celle TOPCon e Back Contact, prezzi FOB Cina, trasporto marittimo, tassi di cambio e prezzi DDP Europa. A cura di Synapsun, esperto di moduli fotovoltaici.",
        "keywords": "prezzi moduli fotovoltaici, barometro prezzi PV, prezzo polisilicio, prezzo wafer solare, prezzo moduli TOPCon, prezzo moduli back contact, prezzo pannelli solari 2025, moduli FOB Cina, trasporto marittimo solare, tasso di cambio EUR USD CNY, Synapsun",
        "canonical": "https://synapsun.com/it/barometer",
        "og_title": "Barometro dei prezzi dei moduli fotovoltaici | Synapsun",
        "og_description": "Monitoraggio settimanale dei prezzi dei moduli fotovoltaici dalla materia prima al modulo consegnato in Europa. TOPCon, Back Contact, FOB Cina, trasporto, tassi di cambio.",
        "og_locale": "it_IT",
        "twitter_title": "Barometro dei prezzi dei moduli fotovoltaici | Synapsun",
        "twitter_description": "Monitoraggio settimanale dei prezzi PV: polisilicio, wafer, moduli TOPCon e Back Contact, trasporto marittimo e tassi di cambio.",
        "ld_name": "Barometro dei prezzi dei moduli fotovoltaici",
        "ld_description": "Serie storiche settimanali dei prezzi della filiera fotovoltaica: polisilicio, wafer, celle, moduli, trasporto marittimo e tassi di cambio EUR/USD/CNY.",
        "ld_inLanguage": "it-IT",
        "breadcrumb_home": "Home",
        "breadcrumb_modules": "Moduli fotovoltaici",
        "breadcrumb_modules_url": "https://synapsun.com/it/moduli-fotovoltaici",
        "breadcrumb_barometer": "Barometro dei prezzi",
        "dataset_name": "Barometro Synapsun — Prezzi dei moduli fotovoltaici",
        "dataset_description": "Serie storiche settimanali dei prezzi della filiera fotovoltaica: polisilicio, wafer, celle, moduli, trasporto marittimo e tassi di cambio EUR/USD/CNY.",
        "license": "https://synapsun.com/it/note-legali",
        "keywords_list": '["fotovoltaico", "moduli solari", "prezzo polisilicio", "TOPCon", "Back Contact", "trasporto marittimo", "tasso di cambio"]',
        "variable_measured": [
            "Prezzo del polisilicio (RMB/kg)",
            "Prezzi dei wafer (USD/W)",
            "Prezzi delle celle (RMB/W)",
            "Prezzi dei moduli FOB Cina (USD/Wp)",
            "Trasporto marittimo Shanghai-Europa (USD/40HC)",
            "Tasso EUR/USD",
            "Tasso EUR/CNY",
            "Prezzi dei moduli DDP Europa (EUR/Wp)",
        ],
    },
    "es": {
        "title": "Barómetro de precios de módulos fotovoltaicos 2025 | Synapsun",
        "description": "Seguimiento semanal de los precios de los módulos fotovoltaicos: polisilicio, obleas, células TOPCon y Back Contact, precios FOB China, transporte marítimo, tipos de cambio y precios DDP Europa. Por Synapsun, experto en módulos fotovoltaicos.",
        "keywords": "precios módulos fotovoltaicos, barómetro precios PV, precio polisilicio, precio oblea solar, precio módulos TOPCon, precio módulos back contact, precio panel solar 2025, módulos FOB China, transporte marítimo solar, tipo de cambio EUR USD CNY, Synapsun",
        "canonical": "https://synapsun.com/es/barometer",
        "og_title": "Barómetro de precios de módulos fotovoltaicos | Synapsun",
        "og_description": "Seguimiento semanal de los precios de módulos fotovoltaicos desde la materia prima hasta el módulo entregado en Europa. TOPCon, Back Contact, FOB China, flete, tipos de cambio.",
        "og_locale": "es_ES",
        "twitter_title": "Barómetro de precios de módulos fotovoltaicos | Synapsun",
        "twitter_description": "Seguimiento semanal de precios PV: polisilicio, obleas, módulos TOPCon y Back Contact, transporte marítimo y tipos de cambio.",
        "ld_name": "Barómetro de precios de módulos fotovoltaicos",
        "ld_description": "Series temporales semanales de los precios de la cadena de valor fotovoltaica: polisilicio, obleas, células, módulos, transporte marítimo y tipos de cambio EUR/USD/CNY.",
        "ld_inLanguage": "es-ES",
        "breadcrumb_home": "Inicio",
        "breadcrumb_modules": "Módulos fotovoltaicos",
        "breadcrumb_modules_url": "https://synapsun.com/es/modulos-fotovoltaicos",
        "breadcrumb_barometer": "Barómetro de precios",
        "dataset_name": "Barómetro Synapsun — Precios de módulos fotovoltaicos",
        "dataset_description": "Series temporales semanales de los precios de la cadena de valor fotovoltaica: polisilicio, obleas, células, módulos, transporte marítimo y tipos de cambio EUR/USD/CNY.",
        "license": "https://synapsun.com/es/aviso-legal",
        "keywords_list": '["fotovoltaico", "módulos solares", "precio polisilicio", "TOPCon", "Back Contact", "transporte marítimo", "tipo de cambio"]',
        "variable_measured": [
            "Precio del polisilicio (RMB/kg)",
            "Precios de las obleas (USD/W)",
            "Precios de las células (RMB/W)",
            "Precios de módulos FOB China (USD/Wp)",
            "Transporte marítimo Shanghái-Europa (USD/40HC)",
            "Tipo EUR/USD",
            "Tipo EUR/CNY",
            "Precios de módulos DDP Europa (EUR/Wp)",
        ],
    },
}


def build_head(lang: str, master_head: str, hreflang_block: str) -> str:
    d = HEADS[lang]
    vm = ",\n".join(f'        "{v}"' for v in d["variable_measured"])
    all_locales = {"fr": "fr_FR", "en": "en_GB", "de": "de_DE", "it": "it_IT", "es": "es_ES"}
    alt_locales = "\n".join(
        f'<meta property="og:locale:alternate" content="{loc}">'
        for l, loc in all_locales.items() if l != lang
    )
    return f"""<html lang="{lang}">
<head>
<meta charset="UTF-8">
<!-- URL par langue (placeholder synapsun.com — à confirmer par l'IT, cf. PROJECT.md > QUESTIONS BLOQUANTES) -->
{hreflang_block}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{d['title']}</title>
<meta name="description" content="{d['description']}">
<meta name="keywords" content="{d['keywords']}">
<meta name="robots" content="index, follow">
<meta name="author" content="Synapsun">
<link rel="canonical" href="{d['canonical']}">

<!-- Open Graph / Facebook -->
<meta property="og:type" content="website">
<meta property="og:url" content="{d['canonical']}">
<meta property="og:title" content="{d['og_title']}">
<meta property="og:description" content="{d['og_description']}">
<meta property="og:image" content="https://synapsun.com/build/img/og-barometre-pv.jpg">
<meta property="og:locale" content="{d['og_locale']}">
{alt_locales}
<meta property="og:site_name" content="Synapsun">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@synapsun">
<meta name="twitter:title" content="{d['twitter_title']}">
<meta name="twitter:description" content="{d['twitter_description']}">
<meta name="twitter:image" content="https://synapsun.com/build/img/og-barometre-pv.jpg">

<!-- Structured Data : WebPage + Dataset -->
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@graph": [
    {{
      "@type": "WebPage",
      "@id": "{d['canonical']}",
      "url": "{d['canonical']}",
      "name": "{d['ld_name']}",
      "description": "{d['ld_description']}",
      "inLanguage": "{d['ld_inLanguage']}",
      "isPartOf": {{ "@id": "https://synapsun.com" }},
      "publisher": {{
        "@type": "Organization",
        "name": "Synapsun",
        "url": "https://synapsun.com",
        "logo": {{
          "@type": "ImageObject",
          "url": "https://synapsun.com/build/img/logos/logo.svg"
        }}
      }},
      "breadcrumb": {{
        "@type": "BreadcrumbList",
        "itemListElement": [
          {{ "@type": "ListItem", "position": 1, "name": "{d['breadcrumb_home']}", "item": "https://synapsun.com" }},
          {{ "@type": "ListItem", "position": 2, "name": "{d['breadcrumb_modules']}", "item": "{d['breadcrumb_modules_url']}" }},
          {{ "@type": "ListItem", "position": 3, "name": "{d['breadcrumb_barometer']}", "item": "{d['canonical']}" }}
        ]
      }}
    }},
    {{
      "@type": "Dataset",
      "name": "{d['dataset_name']}",
      "description": "{d['dataset_description']}",
      "url": "{d['canonical']}",
      "creator": {{
        "@type": "Organization",
        "name": "Synapsun",
        "url": "https://synapsun.com"
      }},
      "keywords": {d['keywords_list']},
      "license": "{d['license']}",
      "temporalCoverage": "2024/..",
      "variableMeasured": [
{vm}
      ]
    }}
  ]
}}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto+Condensed:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
"""


def main():
    master = MASTER.read_text(encoding="utf-8")

    m = re.search(r'<html lang="fr">\n<head>\n(.*?)\n<style>', master, re.S)
    if not m:
        raise SystemExit("Impossible de localiser le bloc <head> du master.")
    master_head = m.group(1)

    hm = re.search(r"(<link rel=\"alternate\".*?x-default[^\n]*\n)", master_head, re.S)
    if not hm:
        raise SystemExit("Bloc hreflang introuvable dans le master.")
    hreflang_block = hm.group(1).rstrip("\n")
    # Retire le commentaire "URL par langue" déjà présent juste avant, pour ne
    # pas le dupliquer (il est réinjecté par build_head).
    hreflang_block = hreflang_block.replace(
        "<!-- URL par langue (placeholder synapsun.com — à confirmer par l'IT, cf. PROJECT.md > QUESTIONS BLOQUANTES) -->\n",
        "",
    )

    head_start = master.index('<html lang="fr">')
    style_start = master.index("<style>", head_start)
    rest_of_file = master[style_start:]  # <style> ... jusqu'à la fin du fichier

    for lang in ("en", "de", "it", "es"):
        new_head = build_head(lang, master_head, hreflang_block)
        out = BANNER + new_head + rest_of_file
        out_path = MASTER.parent / f"barometre-synapsun-{lang}.html"
        out_path.write_text(out, encoding="utf-8")
        print(f"Généré : {out_path.name} ({len(out)} octets)")


if __name__ == "__main__":
    main()

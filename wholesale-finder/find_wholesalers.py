#!/usr/bin/env python3
import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from google_search import GoogleSearchError, search_all
from scraper import fetch_page

COUNTRY_CR = {
    "FR": "countryFR", "DE": "countryDE", "IT": "countryIT", "ES": "countryES",
    "BE": "countryBE", "NL": "countryNL", "GB": "countryUK", "UK": "countryUK",
    "PT": "countryPT", "PL": "countryPL", "AT": "countryAT", "CH": "countryCH",
    "SE": "countrySE", "DK": "countryDK", "IE": "countryIE", "LU": "countryLU",
}

TLD_COUNTRY = {
    "fr": "France", "de": "Germany", "it": "Italy", "es": "Spain", "be": "Belgium",
    "nl": "Netherlands", "uk": "United Kingdom", "co.uk": "United Kingdom",
    "pt": "Portugal", "pl": "Poland", "at": "Austria", "ch": "Switzerland",
    "se": "Sweden", "dk": "Denmark", "ie": "Ireland", "lu": "Luxembourg",
}

GENERAL_QUERY_TEMPLATES = [
    ("general_en", '"{brand}" ("official distributor" OR "authorized distributor" OR '
                    '"wholesale account" OR "become a retailer") Europe'),
    ("general_fr", '"{brand}" ("grossiste officiel" OR "distributeur officiel" OR '
                    '"devenir revendeur" OR "ouvrir un compte professionnel")'),
    ("general_de", '"{brand}" ("offizieller Großhändler" OR "offizieller Distributor" OR '
                    '"Händler werden")'),
    ("general_it", '"{brand}" ("grossista ufficiale" OR "distributore ufficiale" OR '
                    '"diventa rivenditore")'),
    ("general_es", '"{brand}" ("distribuidor oficial" OR "mayorista oficial" OR '
                    '"hazte revendedor")'),
]

SITE_QUERY_TEMPLATES = [
    ("europages_com", 'site:europages.com "{brand}"'),
    ("europages_fr", 'site:europages.fr "{brand}" grossiste'),
    ("europages_de", 'site:europages.de "{brand}" Großhändler'),
    ("kompass_com", 'site:kompass.com "{brand}"'),
]


def guess_country(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    for suffix, country in TLD_COUNTRY.items():
        if netloc.endswith("." + suffix):
            return country
    return ""


def build_cr(countries: list[str]) -> str | None:
    codes = [COUNTRY_CR[c] for c in countries if c in COUNTRY_CR]
    return "|".join(codes) if codes else None


def run(brand: str, countries: list[str], max_results: int, fetch_pages: bool,
        max_fetch: int, output_path: Path) -> None:
    cr = build_cr(countries)
    rows = []
    seen_urls = set()

    all_templates = [(label, tpl, cr) for label, tpl in GENERAL_QUERY_TEMPLATES] + \
                     [(label, tpl, None) for label, tpl in SITE_QUERY_TEMPLATES]

    for label, template, query_cr in all_templates:
        query = template.format(brand=brand)
        print(f"[google] {label}: {query}", file=sys.stderr)
        try:
            items = search_all(query, max_results=max_results, country_restrict=query_cr)
        except GoogleSearchError as exc:
            print(f"  -> erreur: {exc}", file=sys.stderr)
            continue
        for item in items:
            url = item.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            rows.append({
                "brand": brand,
                "query_label": label,
                "title": item.get("title", ""),
                "url": url,
                "domain": urlparse(url).netloc,
                "snippet": item.get("snippet", "").replace("\n", " "),
                "country_hint": guess_country(url),
                "email_found": "",
                "phone_found": "",
                "fetched_ok": "",
            })
        time.sleep(1)

    if fetch_pages and rows:
        to_fetch = rows[:max_fetch]
        print(f"[fetch] enrichissement de {len(to_fetch)} pages (robots.txt respecté)...", file=sys.stderr)
        for row in to_fetch:
            info = fetch_page(row["url"])
            row["email_found"] = "; ".join(info["emails"])
            row["phone_found"] = "; ".join(info["phones"])
            row["fetched_ok"] = str(info["fetched_ok"])
            time.sleep(2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["brand", "query_label", "title", "url", "domain", "snippet",
                  "country_hint", "email_found", "phone_found", "fetched_ok"]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} résultats uniques -> {output_path}", file=sys.stderr)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Recherche des grossistes / distributeurs officiels d'une marque en Europe."
    )
    parser.add_argument("brand", help='Nom de la marque, ex: "Nike"')
    parser.add_argument("--countries", default="", help="Codes pays ISO2 séparés par des virgules, ex: FR,DE,IT")
    parser.add_argument("--max-results", type=int, default=10, help="Résultats max par requête Google (défaut: 10)")
    parser.add_argument("--fetch-pages", action="store_true",
                         help="Aller chercher email/téléphone sur chaque page trouvée (plus lent, respecte robots.txt)")
    parser.add_argument("--max-fetch", type=int, default=20, help="Nombre max de pages à enrichir (défaut: 20)")
    parser.add_argument("--output", default=None, help="Chemin du CSV de sortie")
    args = parser.parse_args()

    countries = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    if args.output:
        output_path = Path(args.output)
    else:
        slug = args.brand.lower().replace(" ", "_")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = Path("results") / f"{slug}_{stamp}.csv"

    run(args.brand, countries, args.max_results, args.fetch_pages, args.max_fetch, output_path)


if __name__ == "__main__":
    main()

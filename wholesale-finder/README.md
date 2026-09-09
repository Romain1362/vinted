# Wholesale Finder

Outil en ligne de commande pour identifier des grossistes / distributeurs
officiels de marques en Europe, en vue d'un achat pour revente sur Amazon.

## Comment ça marche

L'outil ne scrape **jamais** directement les pages de résultats Google
(cela viole les CGU de Google et se fait bloquer très vite). Il utilise à la
place l'**API officielle Google Custom Search**, avec plusieurs modèles de
requêtes :

- des requêtes généralistes multilingues (EN/FR/DE/IT/ES) du type
  `"<marque>" "distributeur officiel" OR "grossiste officiel" OR "wholesale account"`,
- des requêtes ciblées `site:europages.com "<marque>"`,
  `site:kompass.com "<marque>"` pour retrouver les fiches entreprises sur les
  grands annuaires B2B européens.

Avec `--fetch-pages`, l'outil va ensuite chercher email/téléphone sur chaque
page trouvée, en respectant systématiquement le `robots.txt` du site visité
et en s'identifiant avec un User-Agent dédié (voir `robots.py`).

Un fichier `data/trade_show_directories.csv` recense en plus des annuaires
de salons professionnels B2B européens (10Times, Eventseye, AUMA...) utiles
pour repérer des grossistes lors de salons physiques.

## ⚠️ Important

- **Non testé en conditions réelles dans cette session** : l'environnement
  d'exécution qui a servi à écrire cet outil n'a pas d'accès réseau sortant
  (même `example.com` est bloqué). Le code suit les bonnes pratiques
  (API officielle, respect de `robots.txt`, rate limiting) mais tu dois le
  tester chez toi avant de t'y fier.
- **Trouver un contact n'est pas une autorisation.** Pour vendre en tant que
  revendeur légitime d'une marque sur Amazon (notamment si la marque a une
  politique de "brand gating"), il te faudra généralement une **facture
  provenant directement de la marque ou d'un distributeur qu'elle reconnaît
  officiellement**. Vérifie toujours l'authenticité du fournisseur avant de
  commander (numéro de TVA intracommunautaire, avis clients B2B, appel
  téléphonique direct).
- Le contenu de `data/trade_show_directories.csv` vient de connaissances
  générales et n'a pas pu être vérifié en direct pour la même raison
  réseau — revérifie les URLs avant de les partager.

## Installation

```bash
cd wholesale-finder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Obtenir une clé Google Custom Search API (gratuit jusqu'à 100 requêtes/jour)

1. Va sur https://programmablesearchengine.google.com/ et crée un nouveau
   moteur de recherche. Dans ses paramètres, active **"Search the entire
   web"** (sinon il ne cherchera que sur les sites que tu listes toi-même).
   Récupère son **Search engine ID** (CSE ID).
2. Va sur https://console.cloud.google.com/apis/library/customsearch.googleapis.com,
   active l'API "Custom Search API" sur un projet, puis crée une clé API
   dans "Identifiants".
3. Renseigne les deux valeurs dans `.env` :

```
GOOGLE_API_KEY=ta_cle
GOOGLE_CSE_ID=ton_cse_id
```

Le quota gratuit est de 100 requêtes/jour ; au-delà c'est 5$ pour 1000
requêtes (jusqu'à 10 000/jour). Chaque marque recherchée consomme ~9
requêtes (5 générales + 4 site:) par tranche de 10 résultats.

## Utilisation

```bash
# Recherche simple
python find_wholesalers.py "Nike"

# Restreindre à certains pays (utilisé sur les requêtes généralistes)
python find_wholesalers.py "Patagonia" --countries FR,DE,IT,ES,BE,NL

# Plus de résultats par requête + enrichissement email/téléphone
python find_wholesalers.py "The North Face" --max-results 20 --fetch-pages --max-fetch 30

# Sortie vers un fichier précis
python find_wholesalers.py "Levi's" --output results/levis.csv
```

Par défaut, le CSV est écrit dans `results/<marque>_<horodatage>.csv`.

### Colonnes du CSV

| Colonne | Description |
|---|---|
| `brand` | Marque recherchée |
| `query_label` | Modèle de requête ayant produit ce résultat (ex: `europages_com`, `general_fr`) |
| `title` | Titre de la page (issu de Google) |
| `url` | Lien vers la page |
| `domain` | Nom de domaine |
| `snippet` | Extrait Google |
| `country_hint` | Pays deviné depuis le TLD du domaine (heuristique, pas fiable à 100%) |
| `email_found` / `phone_found` | Rempli seulement avec `--fetch-pages` |
| `fetched_ok` | `True`/`False` si la page a pu être visitée (vide si `--fetch-pages` non utilisé) |

## Limites connues

- Les requêtes `site:` ne couvrent qu'Europages et Kompass pour l'instant ;
  ajoute d'autres annuaires en complétant `SITE_QUERY_TEMPLATES` dans
  `find_wholesalers.py`.
- `country_hint` se base uniquement sur le TLD du domaine, pas sur le
  contenu réel de la page.
- L'extraction d'email/téléphone (`scraper.py`) est heuristique (regex) et
  peut manquer des contacts affichés en image ou via un formulaire JS.
- Certaines pages (Kompass notamment) chargent leur contenu en
  JavaScript : l'extraction par `requests`/`BeautifulSoup` ne verra alors
  que le HTML statique. Si besoin, on pourra ajouter un rendu via un
  navigateur headless (Playwright, déjà disponible dans cet environnement)
  dans une itération future.

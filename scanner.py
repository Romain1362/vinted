"""
Swing Trading Scanner
---------------------
Détecte le pattern: tendance haussière MM50 + pullback sur MM50 + reprise MACD.
Exporte les résultats en CSV et au format TradingView.
"""

import time
import sys
import csv
import os
from datetime import datetime

import yfinance as yf
import pandas as pd

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

LOOKBACK_DAYS = "6mo"          # Données historiques à récupérer
SMA_PERIOD = 50                # Période de la moyenne mobile principale
SMA_TREND_WINDOW = 12          # Nb de jours pour juger la pente de la MM50
MACD_FAST = 12                 # EMA rapide MACD
MACD_SLOW = 26                 # EMA lente MACD
MACD_SIGNAL = 9                # EMA signal MACD
MACD_CROSS_LOOKBACK = 3        # Nb de jours pour détecter le croisement histo
PRICE_ABOVE_SMA_MAX = 0.01     # +1 % max au-dessus de la MM50
PRICE_BELOW_SMA_MAX = -0.02    # -2 % max en-dessous de la MM50
VOL_PERIOD = 20                # Période pour la moyenne de volume
VOL_SHORT = 3                  # Nb de jours récents pour le volume moyen court
PAUSE_BETWEEN_TICKERS = 0.3    # Secondes entre requêtes (anti-rate-limit)

OUTPUT_DIR = "results"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE = os.path.join(OUTPUT_DIR, f"scan_{TIMESTAMP}.csv")
TV_FILE = os.path.join(OUTPUT_DIR, f"tradingview_{TIMESTAMP}.txt")

# ─────────────────────────────────────────────
# LISTES DE TICKERS
# ─────────────────────────────────────────────

US_TICKERS = [
    # Semiconducteurs
    "NVDA", "AMD", "AVGO", "TSM", "QCOM", "MU", "TXN", "INTC", "ADI", "NXPI",
    "MRVL", "ON", "MCHP", "SWKS", "QRVO", "ASML", "LRCX", "KLAC", "AMAT", "TER",
    "ENTG",
    # Logiciels
    "MSFT", "CRM", "ORCL", "ADBE", "INTU", "NOW", "SNPS", "CDNS", "WDAY",
    # Cybersécurité
    "PANW", "CRWD", "FTNT", "ZS", "OKTA", "CYBR",
    # Big Tech
    "AAPL", "GOOGL", "META", "AMZN", "NFLX", "CSCO", "IBM", "HPQ", "DELL",
    # Énergie
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "OXY", "WMB", "KMI",
    # Santé / Biotech
    "AMGN", "GILD", "VRTX", "REGN", "BIIB", "MRNA", "UNH", "LLY", "JNJ", "PFE",
    "ABBV", "MRK", "TMO", "ABT", "DHR", "ISRG", "SYK", "BSX",
    # Finance
    "JPM", "BAC", "WFC", "C", "USB", "PNC", "TFC", "GS", "MS", "SCHW",
    "V", "MA", "PYPL", "AXP", "FIS", "FI",
    # Défense / Industrie
    "LMT", "RTX", "NOC", "GD", "BA", "LHX", "TDG", "CAT", "HON", "GE",
    "UNP", "DE", "MMM", "EMR", "ETN", "ITW", "PH",
    # Conso / Retail
    "TSLA", "HD", "NKE", "MCD", "LOW", "SBUX", "BKNG", "TJX", "CMG",
    # Conso défensive
    "PG", "KO", "PEP", "WMT", "COST", "MDLZ", "CL", "KMB", "GIS", "STZ",
    # Utilities / Matériaux / REIT
    "NEE", "DUK", "SO", "AEP", "D", "EXC", "SRE", "XEL",
    "LIN", "FCX", "NEM", "APD", "SHW", "ECL", "NUE",
    "PLD", "AMT", "EQIX", "WELL", "SPG", "O", "PSA", "DLR",
    # Télécoms / Médias
    "DIS", "CMCSA", "T", "VZ", "TMUS", "WBD",
]

EUROPE_TICKERS = [
    # Semiconducteurs
    "ASML.AS", "STM.PA", "BESI.AS",
    # Tech / Logiciels
    "SAP.DE", "CAP.PA", "ATO.PA", "PRX.AS", "DSY.PA",
    # Énergie
    "SHEL.L", "TTE.PA", "BP.L", "EQNR.OL", "ENI.MI", "REP.MC",
    # Pharma / Santé
    "NOVN.SW", "ROG.SW", "SAN.PA", "AZN.L", "NOVO-B.CO", "GSK.L",
    "BAYN.DE", "EL.PA",
    # Finance / Assurance
    "BNP.PA", "GLE.PA", "HSBA.L", "DBK.DE", "ISP.MI", "SAN.MC",
    "UCG.MI", "BARC.L", "ALV.DE", "AXA.PA", "G.MI", "CS.PA",
    # Défense / Aéro
    "AIR.PA", "SAF.PA", "HO.PA", "RHM.DE", "BA.L", "LDO.MI",
    # Industrie
    "SIE.DE", "SU.PA", "ABBN.SW", "KGX.DE",
    # Luxe
    "MC.PA", "RMS.PA", "KER.PA", "CFR.SW", "ADS.DE",
    # Conso défensive
    "NESN.SW", "ULVR.L", "OR.PA", "DGE.L", "HEIA.AS", "ABI.BR",
    # Utilities / Énergie
    "ENEL.MI", "IBE.MC", "ENGI.PA", "EOAN.DE", "RWE.DE",
    # Auto
    "VOW3.DE", "STLA.MI", "BMW.DE", "MBG.DE", "RNO.PA",
    # Chimie / Matériaux
    "AI.PA", "BASF.DE", "GLEN.L", "RIO.L", "UPM.HE",
    # Immobilier
    "VNA.DE",
]

ALL_TICKERS = US_TICKERS + EUROPE_TICKERS

# ─────────────────────────────────────────────
# MAPPING YAHOO SUFFIX → TRADINGVIEW EXCHANGE
# ─────────────────────────────────────────────

SUFFIX_TO_EXCHANGE = {
    ".PA": "EURONEXT",
    ".AS": "EURONEXT",
    ".BR": "EURONEXT",
    ".DE": "XETR",
    ".L":  "LSE",
    ".SW": "SWX",
    ".MI": "MIL",
    ".MC": "BME",
    ".OL": "OSE",
    ".CO": "OMXCOP",
    ".HE": "OMXHEX",
}

def yahoo_to_tradingview(ticker: str) -> str:
    for suffix, exchange in SUFFIX_TO_EXCHANGE.items():
        if ticker.endswith(suffix):
            symbol = ticker[: -len(suffix)]
            return f"{exchange}:{symbol}"
    # Pas de suffixe = marché US (NASDAQ par défaut)
    return f"NASDAQ:{ticker}"

# ─────────────────────────────────────────────
# INDICATEURS TECHNIQUES (calcul manuel)
# ─────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def compute_sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()

def compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

# ─────────────────────────────────────────────
# ANALYSE D'UN TICKER
# ─────────────────────────────────────────────

def analyze_ticker(ticker: str) -> dict | None:
    """
    Retourne un dict de résultats ou None si les données sont insuffisantes.
    """
    try:
        df = yf.download(ticker, period=LOOKBACK_DAYS, interval="1d",
                         progress=False, auto_adjust=True)
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

    if df is None or df.empty or len(df) < SMA_PERIOD + 10:
        return {"ticker": ticker, "error": "Données insuffisantes"}

    # Aplatir les colonnes multi-index si yfinance renvoie un MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"].dropna()
    volume = df["Volume"].dropna()

    if len(close) < SMA_PERIOD + 10:
        return {"ticker": ticker, "error": "Série trop courte après nettoyage"}

    # — SMA50 —
    sma50 = compute_sma(close, SMA_PERIOD)
    current_sma50 = sma50.iloc[-1]
    current_price = close.iloc[-1]

    # Pente MM50 : on compare la valeur actuelle à celle d'il y a SMA_TREND_WINDOW jours
    sma50_past = sma50.iloc[-SMA_TREND_WINDOW - 1]
    sma50_trending_up = current_sma50 > sma50_past

    # Écart prix / MM50
    price_vs_sma_pct = (current_price - current_sma50) / current_sma50

    # Critère 1 : tendance haussière (prix > MM50 ET MM50 orientée hausse)
    crit1_trend = (current_price > current_sma50) and sma50_trending_up

    # Critère 2 : prix dans la zone de pullback autour de la MM50
    crit2_pullback = PRICE_BELOW_SMA_MAX <= price_vs_sma_pct <= PRICE_ABOVE_SMA_MAX

    # — MACD —
    _, _, histogram = compute_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    current_histo = histogram.iloc[-1]

    # Critère 3 : MACD histogramme vient de repasser positif (1-3 derniers jours)
    # → histo actuel > 0, ET au moins une valeur négative dans les MACD_CROSS_LOOKBACK jours précédents
    recent_histo = histogram.iloc[-(MACD_CROSS_LOOKBACK + 1):-1]
    crit3_macd = (current_histo > 0) and (recent_histo < 0).any()

    # — Volume —
    vol_current = volume.iloc[-VOL_SHORT:].mean()
    vol_avg20 = volume.iloc[-VOL_PERIOD:].mean()
    vol_ratio = vol_current / vol_avg20 if vol_avg20 > 0 else 0
    crit4_volume = vol_ratio > 1.0

    # Statut final
    validated = crit1_trend and crit2_pullback and crit3_macd

    return {
        "ticker": ticker,
        "error": "",
        "tv_symbol": yahoo_to_tradingview(ticker),
        "price": round(float(current_price), 4),
        "sma50": round(float(current_sma50), 4),
        "price_vs_sma_pct": round(price_vs_sma_pct * 100, 2),
        "sma50_trending_up": sma50_trending_up,
        "macd_histo": round(float(current_histo), 6),
        "macd_recently_crossed": crit3_macd,
        "vol_ratio": round(vol_ratio, 2),
        "volume_above_avg": crit4_volume,
        "crit1_trend": crit1_trend,
        "crit2_pullback": crit2_pullback,
        "crit3_macd": crit3_macd,
        "validated": validated,
    }

# ─────────────────────────────────────────────
# AFFICHAGE TERMINAL
# ─────────────────────────────────────────────

def print_header():
    print("\n" + "=" * 110)
    print(f"{'SWING TRADING SCANNER':^110}")
    print(f"{'Date: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^110}")
    print("=" * 110)
    header = (
        f"{'TICKER':<12} {'PRIX':>10} {'MM50':>10} {'ÉC.MM50%':>9} "
        f"{'MM50↑':>6} {'HISTO':>10} {'MACD✓':>7} "
        f"{'VOL/AVG':>8} {'VOL✓':>6} {'STATUT':>10}"
    )
    print(header)
    print("-" * 110)

def print_row(r: dict):
    if r.get("error") and not r.get("price"):
        print(f"{'  ' + r['ticker']:<14} {'ERREUR: ' + r['error'][:70]}")
        return
    status = "✅ VALIDÉ" if r["validated"] else "—"
    trend = "✓" if r["sma50_trending_up"] else "✗"
    macd_ok = "✓" if r["crit3_macd"] else "✗"
    vol_ok = "✓" if r["volume_above_avg"] else "✗"
    line = (
        f"{'  ' + r['ticker']:<14} {r['price']:>10.4f} {r['sma50']:>10.4f} "
        f"{r['price_vs_sma_pct']:>+8.2f}% {trend:>6} {r['macd_histo']:>10.6f} "
        f"{macd_ok:>7} {r['vol_ratio']:>7.2f}x {vol_ok:>6} {status:>10}"
    )
    print(line)

# ─────────────────────────────────────────────
# EXPORT CSV
# ─────────────────────────────────────────────

CSV_FIELDS = [
    "ticker", "tv_symbol", "price", "sma50", "price_vs_sma_pct",
    "sma50_trending_up", "macd_histo", "macd_recently_crossed",
    "vol_ratio", "volume_above_avg",
    "crit1_trend", "crit2_pullback", "crit3_macd", "validated", "error",
]

def export_csv(results: list[dict], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"\n📄 CSV exporté → {path}")

def export_tradingview(results: list[dict], path: str):
    validated = [r for r in results if r.get("validated")]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in validated:
            f.write(r["tv_symbol"] + "\n")
    print(f"📺 TradingView exporté → {path}  ({len(validated)} tickers validés)")

# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────

def run_scan(tickers: list[str], sector_filter: str | None = None) -> list[dict]:
    results = []
    total = len(tickers)
    print_header()

    for i, ticker in enumerate(tickers, 1):
        # Progression affichée sur stderr pour ne pas perturber le tableau stdout
        sys.stderr.write(f"\r  [{i}/{total}] Téléchargement : {ticker:<14}")
        sys.stderr.flush()

        result = analyze_ticker(ticker)
        if result is None:
            result = {"ticker": ticker, "error": "Résultat None inattendu"}

        results.append(result)
        print_row(result)

        time.sleep(PAUSE_BETWEEN_TICKERS)

    sys.stderr.write("\r" + " " * 60 + "\r")  # Efface la ligne de progression
    sys.stderr.flush()
    return results

def print_summary(results: list[dict]):
    validated = [r for r in results if r.get("validated")]
    errors = [r for r in results if r.get("error") and not r.get("price")]
    print("\n" + "=" * 110)
    print(f"  RÉSUMÉ : {len(results)} tickers scannés | "
          f"{len(validated)} validés | {len(errors)} erreurs")
    print("=" * 110)
    if validated:
        print("\n  TICKERS VALIDÉS :")
        for r in validated:
            print(f"    {r['tv_symbol']:<30} prix={r['price']:.4f}  "
                  f"ÉcMM50={r['price_vs_sma_pct']:+.2f}%  "
                  f"MACD histo={r['macd_histo']:.6f}  "
                  f"Vol={r['vol_ratio']:.2f}x {'⬆ VOL' if r['volume_above_avg'] else ''}")

# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Swing Trading Scanner")
    parser.add_argument(
        "--market",
        choices=["us", "eu", "all"],
        default="all",
        help="Filtrer par marché (us / eu / all)",
    )
    args = parser.parse_args()

    if args.market == "us":
        tickers = US_TICKERS
    elif args.market == "eu":
        tickers = EUROPE_TICKERS
    else:
        tickers = ALL_TICKERS

    print(f"\nDémarrage du scan sur {len(tickers)} tickers (marché: {args.market.upper()})…")
    print("Appuyez sur Ctrl+C pour interrompre.\n")

    try:
        results = run_scan(tickers)
    except KeyboardInterrupt:
        print("\n\nScan interrompu par l'utilisateur.")
        results = []

    if results:
        print_summary(results)
        export_csv(results, CSV_FILE)
        export_tradingview(results, TV_FILE)

    print("\nScan terminé.\n")

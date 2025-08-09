# fetch_yahoo_es_generic.py
import argparse
import pandas as pd
import yfinance as yf

def main():
    p = argparse.ArgumentParser(description="Télécharge ES=F en intraday depuis Yahoo Finance.")
    p.add_argument("--interval", default="5m", help="1m, 2m, 5m, 15m, 30m, 60m…")
    p.add_argument("--period", default="60d", help="7d, 30d, 60d, 90d… (selon interval)")
    p.add_argument("--start", default="16:00", help="Heure début fenêtre Europe/Paris")
    p.add_argument("--end",   default="17:30", help="Heure fin fenêtre Europe/Paris")
    p.add_argument("--tz",    default="Europe/Paris", help="Timezone locale")
    p.add_argument("--ticker", default="ES=F", help="Ticker Yahoo (ES=F continu)")
    args = p.parse_args()

    df = yf.download(args.ticker, interval=args.interval, period=args.period,
                     auto_adjust=False, prepost=False)
    if df.empty:
        print("❌ Aucune donnée reçue. Essaie un intervalle plus grand (5m/15m) ou une période plus courte.")
        return

    # Harmonise TZ -> Paris
    df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    df = df.tz_convert(args.tz)

    # Colonnes simples
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]

    out = df[["open","high","low","close","volume"]].copy().reset_index()
    # Renommer la première colonne en "timestamp"
    out = out.rename(columns={out.columns[0]: "timestamp"})

    # Filtre horaire (Paris)
    h_debut = pd.to_datetime(args.start).time()
    h_fin   = pd.to_datetime(args.end).time()
    mask = (out["timestamp"].dt.time >= h_debut) & (out["timestamp"].dt.time <= h_fin)
    out_win = out.loc[mask].copy()

    # Sauvegardes
    base = f"ES_F_{args.interval}_{args.period}"
    full_csv = f"{base}.csv"
    win_csv  = f"{base}_{args.start.replace(':','h')}_{args.end.replace(':','h')}_FR.csv"

    out.to_csv(full_csv, index=False)
    out_win.to_csv(win_csv, index=False)

    print(f"✅ Enregistré {len(out)} lignes -> {full_csv}")
    print(f"✅ Enregistré {len(out_win)} lignes ({args.start}-{args.end}) -> {win_csv}")

if __name__ == "__main__":
    main()

import pandas as pd
import yfinance as yf

# Paramètres
TICKER = "ES=F"     # E-mini S&P 500 continu
INTERVAL = "1m"     # Intervalle 1 minute (disponible ~7 jours)
PERIOD = "7d"       # Fenêtre max pour 1m sur Yahoo
LOCAL_TZ = "Europe/Paris"
FENETRE_DEBUT = "16:00"
FENETRE_FIN = "17:30"

def main():
    # Téléchargement
    df = yf.download(TICKER, interval=INTERVAL, period=PERIOD, auto_adjust=False, prepost=False)
    if df.empty:
        print("❌ Aucune donnée reçue de Yahoo. Essaie 2m/5m ou réduis la période.")
        return

    # Timezone -> Paris
    df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    df = df.tz_convert(LOCAL_TZ)

    # Colonnes en minuscules
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]

    # Garder OHLCV
    out = df[["open", "high", "low", "close", "volume"]].copy().reset_index()

    # Renommer date -> timestamp
    col_date = out.columns[0]
    out = out.rename(columns={col_date: "timestamp"})

    # Filtre horaire (Paris)
    h_debut = pd.to_datetime(FENETRE_DEBUT).time()
    h_fin = pd.to_datetime(FENETRE_FIN).time()
    masque = (out["timestamp"].dt.time >= h_debut) & (out["timestamp"].dt.time <= h_fin)
    out_win = out.loc[masque].copy()

    # Sauvegarde
    full_csv = "ES_F_1m_7jours.csv"
    win_csv = "ES_F_1m_7jours_16h_17h30_FR.csv"
    out.to_csv(full_csv, index=False)
    out_win.to_csv(win_csv, index=False)

    print(f"✅ Enregistré {len(out)} lignes -> {full_csv}")
    print(f"✅ Enregistré {len(out_win)} lignes (16h-17h30) -> {win_csv}")

if __name__ == "__main__":
    main()


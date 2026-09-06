"""
Analyser og visualiser værdata fra vaerdata.csv
=================================================

Leser inn værdata samlet av vaer_pipeline.py, skriver ut nøkkeltall,
og lager grafer som lagres som PNG-filer.

Installer avhengigheter (hvis du ikke har det fra før):
    pip install pandas matplotlib

Kjør:
    python analyser_vaer.py
"""

import logging
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_FIL = Path("vaerdata.csv")
GRAF_MAPPE = Path("grafer")


def last_data(filsti: Path = DATA_FIL) -> pd.DataFrame:
    if not filsti.exists():
        raise Exception(
            f"Fant ikke {filsti}. Kjør vaer_pipeline.py minst én gang først."
        )

    df = pd.read_csv(filsti, parse_dates=["tidspunkt"])
    df = df.sort_values("tidspunkt")
    logger.info(f"Lastet {len(df)} rader for {df['by'].nunique()} by(er)")
    return df


def skriv_ut_nokkeltall(df: pd.DataFrame) -> None:
    print("\n=== Gjennomsnitt per by ===")
    print(df.groupby("by")["temperatur_c"].mean().round(1))

    print("\n=== Høyeste temperatur registrert ===")
    hoyest = df.loc[df["temperatur_c"].idxmax()]
    print(f"{hoyest['temperatur_c']}°C i {hoyest['by']} ({hoyest['tidspunkt']})")

    print("\n=== Laveste temperatur registrert ===")
    lavest = df.loc[df["temperatur_c"].idxmin()]
    print(f"{lavest['temperatur_c']}°C i {lavest['by']} ({lavest['tidspunkt']})")

    print("\n=== Antall målinger per by ===")
    print(df["by"].value_counts())
    print()


def lag_temperaturtrend_graf(df: pd.DataFrame, mappe: Path) -> Path:
    """Linjediagram: temperatur over tid, én linje per by."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for by, gruppe in df.groupby("by"):
        ax.plot(gruppe["tidspunkt"], gruppe["temperatur_c"], marker="o", label=by)

    ax.set_title("Temperaturutvikling over tid")
    ax.set_xlabel("Tidspunkt")
    ax.set_ylabel("Temperatur (°C)")
    ax.legend(title="By")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    fil = mappe / "temperaturtrend.png"
    fig.savefig(fil, dpi=150)
    plt.close(fig)
    return fil


def lag_gjennomsnitt_graf(df: pd.DataFrame, mappe: Path) -> Path:
    """Søylediagram: gjennomsnittstemperatur per by."""
    gjennomsnitt = df.groupby("by")["temperatur_c"].mean().sort_values()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(gjennomsnitt.index, gjennomsnitt.values, color="#4C72B0")

    ax.set_title("Gjennomsnittstemperatur per by")
    ax.set_xlabel("By")
    ax.set_ylabel("Temperatur (°C)")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()

    fil = mappe / "gjennomsnitt_per_by.png"
    fig.savefig(fil, dpi=150)
    plt.close(fig)
    return fil


def lag_fuktighet_graf(df: pd.DataFrame, mappe: Path) -> Path:
    """Linjediagram: luftfuktighet over tid, én linje per by."""
    fig, ax = plt.subplots(figsize=(10, 5))

    for by, gruppe in df.groupby("by"):
        ax.plot(gruppe["tidspunkt"], gruppe["fuktighet_prosent"], marker="o", label=by)

    ax.set_title("Luftfuktighet over tid")
    ax.set_xlabel("Tidspunkt")
    ax.set_ylabel("Fuktighet (%)")
    ax.legend(title="By")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    fil = mappe / "fuktighet_over_tid.png"
    fig.savefig(fil, dpi=150)
    plt.close(fig)
    return fil


def kjor_analyse() -> None:
    df = last_data()
    skriv_ut_nokkeltall(df)

    GRAF_MAPPE.mkdir(exist_ok=True)

    if df["by"].nunique() < 1 or len(df) < 2:
        logger.warning("For lite data til å lage meningsfulle grafer ennå. Samle mer data først.")
        return

    filer = [
        lag_temperaturtrend_graf(df, GRAF_MAPPE),
        lag_gjennomsnitt_graf(df, GRAF_MAPPE),
        lag_fuktighet_graf(df, GRAF_MAPPE),
    ]

    logger.info(f"Lagret {len(filer)} grafer i mappen '{GRAF_MAPPE}':")
    for fil in filer:
        logger.info(f"  - {fil}")


if __name__ == "__main__":
    kjor_analyse()
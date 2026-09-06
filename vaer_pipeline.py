"""
Data pipeline for OpenWeatherMap API
=====================================

Henter værdata for en gitt by, renser dataene, og lagrer dem i en CSV-fil.
Hver kjøring legger til en ny rad, slik at du bygger opp historikk over tid.

Oppsett:
1. Registrer deg gratis på https://openweathermap.org/api
2. Hent API-nøkkelen din (kan ta noen minutter før den aktiveres)
3. Sett den som miljøvariabel:
   - Windows (PowerShell): $env:OWM_API_KEY = "din-nøkkel"
   - Mac/Linux: export OWM_API_KEY="din-nøkkel"
4. Installer avhengigheter: pip install requests pandas

Kjør:
    python vaer_pipeline.py
    python vaer_pipeline.py --by "Bergen"
    python vaer_pipeline.py --by "Stavanger" "Bergen" "Trondheim"
"""

import os
import time
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests
import pandas as pd

# ---------------------------------------------------------------------------
# Logging - strukturert logging for feilsøking og kjøringsstatus
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

API_URL = "https://api.openweathermap.org/data/2.5/weather"
OUTPUT_FIL = Path("vaerdata.csv")


# ---------------------------------------------------------------------------
# 1. EXTRACT - hente rådata fra OpenWeatherMap API
# ---------------------------------------------------------------------------
def hent_vaerdata(by: str, api_nokkel: str, max_forsok: int = 3) -> dict:
    """Henter værdata for én by. Prøver på nytt ved feil (exponential backoff)."""
    params = {
        "q": by,
        "appid": api_nokkel,
        "units": "metric",   # gir Celsius i stedet for Kelvin
        "lang": "no",
    }

    for forsok in range(1, max_forsok + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception(
                    "API-nøkkelen ble avvist. Sjekk at den er riktig, "
                    "og at den er aktivert (kan ta litt tid etter registrering)."
                ) from e
            elif response.status_code == 404:
                raise Exception(f"Fant ikke byen '{by}'. Sjekk stavemåten.") from e
            else:
                logger.warning(f"HTTP-feil ({response.status_code}), forsøk {forsok}/{max_forsok}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Nettverksfeil: {e}, forsøk {forsok}/{max_forsok}")

        if forsok < max_forsok:
            ventetid = 2 ** forsok  # 2, 4, 8 sekunder
            time.sleep(ventetid)

    raise Exception(f"Klarte ikke hente værdata for '{by}' etter {max_forsok} forsøk")


# ---------------------------------------------------------------------------
# 2. TRANSFORM - valider og transformer API-data til et standardisert format
# ---------------------------------------------------------------------------
def transformer_data(rådata: dict) -> dict:
    """Plukker ut relevante felt fra det rå API-svaret og validerer dem."""
    try:
        rad = {
            "tidspunkt": datetime.now(timezone.utc).isoformat(),
            "by": rådata["name"],
            "temperatur_c": rådata["main"]["temp"],
            "foles_som_c": rådata["main"]["feels_like"],
            "fuktighet_prosent": rådata["main"]["humidity"],
            "vaer_beskrivelse": rådata["weather"][0]["description"],
            "vind_meter_sek": rådata["wind"]["speed"],
        }
    except (KeyError, IndexError) as e:
        raise Exception(f"Uventet API-format, mangler felt: {e}")

    # Enkel validering - fanger opp åpenbart feil data før vi lagrer
    if not (-90 <= rad["temperatur_c"] <= 60):
        raise Exception(f"Mistenkelig temperaturverdi: {rad['temperatur_c']}°C")

    return rad


# ---------------------------------------------------------------------------
# 3. LOAD - lagre transformerte værdata i CSV-format
# ---------------------------------------------------------------------------
def last_inn(rad: dict, filsti: Path = OUTPUT_FIL) -> None:
    ny_rad_df = pd.DataFrame([rad])

    if filsti.exists():
        ny_rad_df.to_csv(filsti, mode="a", header=False, index=False)
    else:
        ny_rad_df.to_csv(filsti, mode="w", header=True, index=False)

    logger.info(f"Lagret rad for {rad['by']} i {filsti}")


# ---------------------------------------------------------------------------
# Sette hele pipelinen sammen - kjøres for ÉN by
# ---------------------------------------------------------------------------
def kjor_for_by(by: str, api_nokkel: str) -> bool:
    """Kjører hele ETL-flyten for én by. Returnerer True/False for suksess,
    slik at én mislykket by ikke stopper resten av kjøringen."""
    try:
        logger.info(f"Starter pipeline for by: {by}")

        rådata = hent_vaerdata(by, api_nokkel)
        rad = transformer_data(rådata)
        last_inn(rad)

        logger.info(
            f"Ferdig: {rad['temperatur_c']}°C, {rad['vaer_beskrivelse']} i {rad['by']}"
        )
        return True

    except Exception as e:
        # Fanger feil per by, slik at f.eks. en skrivefeil i ett bynavn
        # ikke hindrer at de andre byene blir hentet.
        logger.error(f"Feilet for '{by}': {e}")
        return False


# ---------------------------------------------------------------------------
# Kjøre pipelinen for én eller flere byer
# ---------------------------------------------------------------------------
def kjor_pipeline(byer: list[str]) -> None:
    api_nokkel = os.environ.get("OWM_API_KEY")
    if not api_nokkel:
        raise Exception(
            "Fant ingen API-nøkkel. Sett miljøvariabelen OWM_API_KEY "
            "(se instruksjonene øverst i filen)."
        )

    logger.info(f"Kjører pipeline for {len(byer)} by(er): {', '.join(byer)}")

    resultater = {"ok": 0, "feilet": 0}

    for by in byer:
        suksess = kjor_for_by(by, api_nokkel)
        if suksess:
            resultater["ok"] += 1
        else:
            resultater["feilet"] += 1

        # Liten pause mellom kall - snill mot API-et og unngår rate limiting
        if by != byer[-1]:
            time.sleep(1)

    logger.info(
        f"Pipeline ferdig: {resultater['ok']} vellykket, "
        f"{resultater['feilet']} feilet av {len(byer)} totalt"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hent værdata og legg til i CSV-historikk")
    parser.add_argument(
        "--by",
        nargs="+",              # godtar én eller flere verdier
        default=["Oslo"],
        help='Én eller flere byer, f.eks. --by "Stavanger" "Bergen" "Trondheim"',
    )
    args = parser.parse_args()

    kjor_pipeline(args.by)
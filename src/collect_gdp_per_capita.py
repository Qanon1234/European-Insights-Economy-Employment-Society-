"""Download EU GDP per capita from Eurostat without transforming the response."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


DATASET_ID = "nama_10_pc"
API_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    + DATASET_ID
)
# Current EU membership, applied consistently to the entire historical period.
# Eurostat uses EL for Greece rather than GR.
EU_COUNTRIES = (
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "EL", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
)
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def main():
    params = [
        ("format", "JSON"), ("lang", "EN"), ("freq", "A"),
        ("unit", "CP_EUR_HAB"), ("na_item", "B1GQ"),
        ("sinceTimePeriod", "2000"),
    ]
    params.extend(("geo", country) for country in EU_COUNTRIES)
    response = requests.get(API_URL, params=params, timeout=(15, 120))
    response.raise_for_status()
    payload = response.json()
    # Reject API errors or asynchronous notices rather than saving them as data.
    if payload.get("class") != "dataset" or not payload.get("value"):
        raise ValueError("Eurostat did not return a populated JSON-stat dataset.")

    time_index = payload["dimension"]["time"]["category"]["index"]
    years = (
        sorted(time_index, key=time_index.get)
        if isinstance(time_index, dict) else list(time_index)
    )
    retrieved = datetime.now(timezone.utc)
    stem = "nama_10_pc_eu27_gdp_per_capita_" + retrieved.strftime("%Y%m%dT%H%M%S%fZ")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / (stem + ".json")
    # Write the original response body bytes, not a reserialized JSON object.
    raw_path.write_bytes(response.content)
    metadata = {
        "dataset_id": DATASET_ID,
        "dataset_title": payload.get("label"),
        "source_url": response.url,
        "dataset_url": "https://ec.europa.eu/eurostat/databrowser/view/nama_10_pc/default/table?lang=en",
        "retrieved_at_utc": retrieved.isoformat(),
        "eurostat_updated": payload.get("updated"),
        "unit": "CP_EUR_HAB",
        "unit_label": "Current prices, euro per capita",
        "national_accounts_item": "B1GQ",
        "frequency": "A",
        "country_codes": list(EU_COUNTRIES),
        "requested_start_year": 2000,
        "returned_years": years,
        "coverage_note": "Time dimension categories; individual observations may be missing.",
        "raw_file": raw_path.name,
        "sha256": hashlib.sha256(response.content).hexdigest(),
    }
    metadata_path = RAW_DIR / (stem + ".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved original response: {raw_path}")
    print(f"Saved collection metadata: {metadata_path}")
    print(f"Returned years: {', '.join(years)}")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Collection failed: {exc}", file=sys.stderr)
        sys.exit(1)

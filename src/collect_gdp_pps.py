"""Collect tec00114 unchanged and report coverage and observation flags."""

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from itertools import product

import requests

from collect_gdp_per_capita import EU_COUNTRIES, RAW_DIR


DATASET_ID = "tec00114"
API_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/" + DATASET_ID
INDICATOR = "VI_PPS_EU27_2020_HAB"


def categories(payload, dimension):
    index = payload["dimension"][dimension]["category"]["index"]
    return sorted(index, key=index.get) if isinstance(index, dict) else list(index)


def cell(payload, coordinates):
    """Locate a JSON-stat observation using its declared dimension order."""
    offset = 0
    for dimension, size in zip(payload["id"], payload["size"]):
        codes = categories(payload, dimension)
        code = coordinates.get(dimension)
        if code is None:
            if len(codes) != 1:
                raise ValueError(f"Unselected dimension: {dimension}")
            code = codes[0]
        if code not in codes:
            return None, None
        offset = offset * size + codes.index(code)

    def lookup(field):
        values = payload.get(field, {})
        return values[offset] if isinstance(values, list) else values.get(str(offset))

    return lookup("value"), lookup("status")


def main(dataset_id=DATASET_ID, end_year=None):
    api_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/" + dataset_id
    params = [
        ("format", "JSON"), ("lang", "EN"), ("freq", "A"),
        ("indic_ppp", INDICATOR), ("ppp_cat18", "GDP"),
        ("sinceTimePeriod", "2000"),
    ]
    if end_year is not None:
        params.append(("untilTimePeriod", str(end_year)))
    params.extend(("geo", country) for country in EU_COUNTRIES)
    response = requests.get(api_url, params=params, timeout=(15, 120))
    response.raise_for_status()
    payload = response.json()
    if payload.get("class") != "dataset" or not payload.get("value"):
        raise ValueError("Eurostat did not return a populated JSON-stat dataset.")
    if categories(payload, "indic_ppp") != [INDICATOR]:
        raise ValueError("Unexpected purchasing power indicator.")
    if categories(payload, "freq") != ["A"] or categories(payload, "ppp_cat18") != ["GDP"]:
        raise ValueError("Unexpected frequency or GDP category.")
    years = categories(payload, "time")
    latest = max(map(int, years))
    requested_end = end_year if end_year is not None else latest
    requested_years = [str(year) for year in range(2000, requested_end + 1)]
    missing = []
    flagged = []
    for country, year in product(EU_COUNTRIES, requested_years):
        value, status = cell(payload, {"geo": country, "time": year})
        if value is None:
            missing.append({"geo": country, "year": year})
        if status:
            flagged.append({"geo": country, "year": year, "status": status})
    quality = {
        "expected_country_year_cells": len(EU_COUNTRIES) * len(requested_years),
        "missing_count": len(missing),
        "missing_observations": missing,
        "years_not_returned": [year for year in requested_years if year not in years],
        "countries_not_returned": sorted(set(EU_COUNTRIES) - set(categories(payload, "geo"))),
        "flag_counts": dict(Counter(item["status"] for item in flagged)),
        "flag_labels": payload.get("extension", {}).get("status", {}).get("label", {}),
        "flagged_observations": flagged,
    }
    retrieved = datetime.now(timezone.utc)
    stem = dataset_id + "_eu27_gdp_pps_" + retrieved.strftime("%Y%m%dT%H%M%S%fZ")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / (stem + ".json")
    # Exclusive creation preserves every previous download. No reserialization.
    with raw_path.open("xb") as output:
        output.write(response.content)
    metadata = {
        "dataset_id": dataset_id,
        "dataset_title": payload.get("label"),
        "dataset_url": f"https://ec.europa.eu/eurostat/databrowser/view/{dataset_id}/default/table?lang=en",
        "source_url": response.url,
        "retrieved_at_utc": retrieved.isoformat(),
        "eurostat_updated": payload.get("updated"),
        "indicator": INDICATOR,
        "category": "GDP",
        "frequency": "A",
        "indicator_label": payload["dimension"]["indic_ppp"]["category"]["label"][INDICATOR],
        "reference": "EU27_2020 = 100 in each year; not a currency amount",
        "country_codes": list(EU_COUNTRIES),
        "requested_start_year": 2000,
        "requested_end_year": end_year,
        "returned_years": years,
        "raw_file": raw_path.name,
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "quality_check": quality,
    }
    with (RAW_DIR / (stem + ".metadata.json")).open("x", encoding="utf-8") as output:
        json.dump(metadata, output, indent=2)
        output.write("\n")
    print(f"Saved original response: {raw_path}")
    print(f"Returned years: {', '.join(years)}")
    print(f"Missing cells (2000 through {requested_end}): {len(missing)}")
    print(f"Years not returned: {quality['years_not_returned']}")
    print(f"Countries not returned: {quality['countries_not_returned']}")
    print(f"Quality flags: {quality['flag_counts']}; labels: {quality['flag_labels']}")
    print("Country | 2000 | 2010 | 2020 | 2025")
    for country in ("SE", "PL", "DE", "EL", "RO"):
        cells = []
        for year in ("2000", "2010", "2020", "2025"):
            value, status = cell(payload, {"geo": country, "time": year})
            cells.append((str(value) if value is not None else "N/A") + (f" [{status}]" if status else ""))
        print(payload["dimension"]["geo"]["category"]["label"][country] + " | " + " | ".join(cells))


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError, KeyError, OSError) as exc:
        print(f"Collection failed: {exc}", file=sys.stderr)
        sys.exit(1)

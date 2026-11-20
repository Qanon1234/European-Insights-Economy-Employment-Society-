"""Hämta och förbered real BNP. Ingen analys och inga diagram."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp"
COUNTRIES = {"IT": "Italy", "ES": "Spain", "PT": "Portugal", "EL": "Greece",
             "MT": "Malta", "CY": "Cyprus", "EU27_2020": "European Union - 27 countries (from 2020)"}
UNITS = {"CLV_I20": "real_gdp_index", "CLV_PCH_PRE": "annual_real_gdp_growth"}
YEARS = range(2000, 2026)


def categories(payload, dimension):
    index = payload["dimension"][dimension]["category"]["index"]
    return sorted(index, key=index.get) if isinstance(index, dict) else list(index)


def lookup(payload, unit, country, year, field):
    # JSON-stat lagrar en flerdimensionell tabell som en platt lista.
    coordinates = {"freq": "A", "na_item": "B1GQ", "unit": unit,
                   "geo": country, "time": str(year)}
    offset = 0
    for dimension, size in zip(payload["id"], payload["size"]):
        codes = categories(payload, dimension)
        if coordinates[dimension] not in codes:
            return None
        offset = offset * size + codes.index(coordinates[dimension])
    values = payload.get(field, {})
    return values[offset] if isinstance(values, list) else values.get(str(offset))


def prepare(payload):
    if payload.get("class") != "dataset" or not payload.get("value"):
        raise ValueError("API-svaret är inte en befolkad JSON-stat-tabell.")
    if payload.get("extension", {}).get("id", "").lower() != "nama_10_gdp":
        raise ValueError("Fel dataset.")
    if set(payload["id"]) != {"freq", "unit", "na_item", "geo", "time"}:
        raise ValueError("Oväntade dimensioner.")
    for dimension, expected in {"freq": {"A"}, "na_item": {"B1GQ"}}.items():
        if set(categories(payload, dimension)) != expected:
            raise ValueError(f"Fel urval: {dimension}")
    if not set(categories(payload, "unit")).issubset(UNITS):
        raise ValueError("Oväntad enhet.")
    if not set(categories(payload, "geo")).issubset(COUNTRIES):
        raise ValueError("Oväntat land.")
    if not set(categories(payload, "time")).issubset({str(y) for y in YEARS}):
        raise ValueError("År utanför 2000–2025.")
    if [len(categories(payload, dim)) for dim in payload["id"]] != payload["size"]:
        raise ValueError("Dimensionernas storlek stämmer inte.")

    labels = payload["dimension"]["geo"]["category"].get("label", {})
    rows = []
    # En rad per land och år. Varje mått får en egen kvalitetsflagga.
    for country, year in product(COUNTRIES, YEARS):
        row = {"country": labels.get(country, COUNTRIES[country]), "country_code": country, "year": year}
        for unit, column in UNITS.items():
            value = lookup(payload, unit, country, year, "value")
            flag = lookup(payload, unit, country, year, "status")
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValueError(f"Icke-numeriskt värde: {country}, {year}, {unit}")
            if flag is not None and not isinstance(flag, str):
                raise ValueError("Kvalitetsflaggan är inte text.")
            row[column] = value
            row[column + "_flag"] = flag
        rows.append(row)
    table = pd.DataFrame(rows)
    for column in table:
        dtype = "Float64" if column in UNITS.values() else "Int64" if column == "year" else "string"
        table[column] = table[column].astype(dtype)
    duplicates = int(table.duplicated(["country_code", "year"]).sum())
    if duplicates:
        raise ValueError("Dubbla land–år upptäcktes.")
    report = {
        "rows": len(table), "expected_rows": len(COUNTRIES) * len(YEARS),
        "returned_country_codes": categories(payload, "geo"),
        "returned_years": categories(payload, "time"),
        "returned_units": categories(payload, "unit"),
        "duplicate_country_years": duplicates,
        "missing_values_by_column": {key: int(value) for key, value in table.isna().sum().items()},
        "data_types": {key: str(value) for key, value in table.dtypes.items()},
        "flag_labels": payload.get("extension", {}).get("status", {}).get("label", {}),
        "units": {},
    }
    for unit, column in UNITS.items():
        missing = table.loc[table[column].isna(), ["country_code", "year"]]
        present = table.loc[table[column].notna()]
        report["units"][unit] = {
            "non_missing_observations": len(present),
            "missing_observations": missing.to_dict("records"),
            "available_years_by_country": {
                country: present.loc[present.country_code.eq(country), "year"].tolist()
                for country in COUNTRIES
            },
            "flag_counts": {str(k): int(v) for k, v in table[column + "_flag"].dropna().value_counts().items()},
        }
    return table, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Validera sparad rå-JSON i stället för att hämta data.")
    parser.add_argument("--validate-csv", type=Path, help="Jämför en befintlig CSV med rå-JSON; kräver --input.")
    args = parser.parse_args()
    if args.validate_csv and not args.input:
        parser.error("--validate-csv kräver --input")
    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        table, report = prepare(payload)
        if args.validate_csv:
            restored = pd.read_csv(args.validate_csv, dtype=table.dtypes.to_dict(),
                                   keep_default_na=False, na_values=[""])
            pd.testing.assert_frame_equal(table, restored)
            print("CSV stämmer med rådata, inklusive värden och flaggor.")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    params = [("format", "JSON"), ("lang", "EN"), ("freq", "A"), ("na_item", "B1GQ"),
              ("sinceTimePeriod", "2000"), ("untilTimePeriod", "2025")]
    params.extend(("unit", unit) for unit in UNITS)
    params.extend(("geo", country) for country in COUNTRIES)
    response = requests.get(API, params=params, timeout=(15, 120))
    response.raise_for_status()
    payload = response.json()
    table, report = prepare(payload)
    downloaded = datetime.now(timezone.utc)
    stem = "nama_10_gdp_real_south_eu_2000_2025_" + downloaded.strftime("%Y%m%dT%H%M%S%fZ")
    raw = ROOT / "data/raw" / (stem + ".json")
    csv = ROOT / "data/processed" / (stem + ".csv")
    raw.parent.mkdir(parents=True, exist_ok=True)
    csv.parent.mkdir(parents=True, exist_ok=True)
    # Spara API-svarets kropp oförändrad, utan att skriva om JSON-formatet.
    with raw.open("xb") as output:
        output.write(response.content)
    table.to_csv(csv, index=False, encoding="utf-8", na_rep="", mode="x")
    restored = pd.read_csv(csv, dtype=table.dtypes.to_dict(), keep_default_na=False, na_values=[""])
    pd.testing.assert_frame_equal(table, restored)
    metadata = {
        "dataset_id": "nama_10_gdp", "dataset_title": payload.get("label"),
        "source_url": response.url,
        "dataset_url": "https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en",
        "downloaded_at_utc": downloaded.isoformat(), "eurostat_updated": payload.get("updated"),
        "frequency": "A", "national_accounts_indicator": "B1GQ",
        "requested_country_codes": list(COUNTRIES), "requested_years": [2000, 2025],
        "units": {unit: payload["dimension"]["unit"]["category"]["label"].get(unit)
                  for unit in UNITS},
        "raw_file": raw.name, "processed_file": csv.name,
        "raw_sha256": hashlib.sha256(response.content).hexdigest(),
        "processed_sha256": hashlib.sha256(csv.read_bytes()).hexdigest(),
        "validation": report,
        "missing_note": "Tomma mått är saknade värden. Tom flagga betyder ingen angiven flagga.",
    }
    meta = raw.with_suffix(".metadata.json")
    with meta.open("x", encoding="utf-8") as output:
        json.dump(metadata, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(f"Rådata: {raw}\nMetadata: {meta}\nCSV: {csv}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("CSV-kontroll mot rådata godkänd. Befintliga filer har inte skrivits över.")


if __name__ == "__main__":
    main()

"""Reshape a saved historical Eurostat response; no network requests."""

import argparse
import json
from itertools import product
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = set("AT BE BG HR CY CZ DK EE FI FR DE EL HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())


def codes(payload, dimension):
    index = payload["dimension"][dimension]["category"]["index"]
    return sorted(index, key=index.get) if isinstance(index, dict) else list(index)


def observation(payload, field, offset):
    values = payload.get(field, {})
    return values[offset] if isinstance(values, list) else values.get(str(offset))


def transform(payload):
    """Decode JSON-stat positions before building typed Pandas columns."""
    if payload.get("class") != "dataset" or payload.get("extension", {}).get("id", "").lower() != "prc_ppp_ind_1":
        raise ValueError("Expected the saved prc_ppp_ind_1 JSON-stat dataset.")
    for dimension, expected in {
        "freq": ["A"], "ppp_cat18": ["GDP"],
        "indic_ppp": ["VI_PPS_EU27_2020_HAB"],
    }.items():
        if codes(payload, dimension) != expected:
            raise ValueError(f"Unexpected selection for {dimension}.")
    dimensions = payload["id"]
    if set(dimensions) != {"freq", "ppp_cat18", "indic_ppp", "geo", "time"}:
        raise ValueError("Unexpected dataset dimensions.")
    axes = [codes(payload, dimension) for dimension in dimensions]
    if [len(axis) for axis in axes] != payload["size"]:
        raise ValueError("Dimension sizes do not match their category indexes.")
    rows = []
    # JSON-stat flattens a multidimensional table; its final dimension varies fastest.
    for offset, coordinates in enumerate(product(*axes)):
        coordinate = dict(zip(dimensions, coordinates))
        value = observation(payload, "value", offset)
        flag = observation(payload, "status", offset)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError(f"Non-numeric PPS value at position {offset}: {value!r}")
        if flag is not None and not isinstance(flag, str):
            raise ValueError(f"Non-text quality flag at position {offset}.")
        rows.append({
            "country": payload["dimension"]["geo"]["category"]["label"][coordinate["geo"]],
            "country_code": coordinate["geo"],
            "year": coordinate["time"],
            "pps_index": value,
            "quality_flag": flag,
        })
    table = pd.DataFrame(rows)
    # Nullable dtypes keep unavailable observations missing rather than making zeros.
    for column in ("country", "country_code", "quality_flag"):
        table[column] = table[column].astype("string")
    table["year"] = pd.to_numeric(table["year"], errors="raise").astype("Int64")
    table["pps_index"] = pd.array(table["pps_index"], dtype="Float64")
    return table.sort_values(["country_code", "year"]).reset_index(drop=True)


def validate(table):
    expected = set(product(COUNTRIES, range(2000, 2026)))
    actual = set(zip(table["country_code"], table["year"]))
    expected_types = {
        "country": "string", "country_code": "string", "year": "Int64",
        "pps_index": "Float64", "quality_flag": "string",
    }
    report = {
        "rows": len(table), "countries": int(table["country_code"].nunique()),
        "year_min": int(table["year"].min()), "year_max": int(table["year"].max()),
        "missing_values_by_column": {key: int(value) for key, value in table.isna().sum().items()},
        "duplicate_country_year_rows": int(table.duplicated(["country_code", "year"]).sum()),
        "missing_country_year_combinations": len(expected - actual),
        "unexpected_country_year_combinations": len(actual - expected),
        "data_types": {column: str(dtype) for column, dtype in table.dtypes.items()},
        "incorrect_data_types": [column for column, dtype in expected_types.items() if str(table[column].dtype) != dtype],
        "quality_flags": {str(key): int(value) for key, value in table["quality_flag"].dropna().value_counts().items()},
    }
    if (report["duplicate_country_year_rows"] or report["incorrect_data_types"]
            or report["missing_country_year_combinations"] or report["unexpected_country_year_combinations"]):
        raise ValueError("Validation failed:\n" + json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Saved raw JSON; defaults to latest historical download.")
    args = parser.parse_args()
    candidates = sorted((ROOT / "data" / "raw").glob("prc_ppp_ind_1_eu27_gdp_pps_*Z.json"))
    source = args.input if args.input is not None else (candidates[-1] if candidates else None)
    if source is None:
        raise FileNotFoundError("No saved historical PPS response found.")
    payload = json.loads(source.read_text(encoding="utf-8"))
    table = transform(payload)
    report = validate(table)
    destination = ROOT / "data" / "processed" / "gdp_pps_2000_2025.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(destination, index=False, na_rep="", encoding="utf-8")
    # Check that serialization preserves every value and flag with explicit dtypes.
    restored = pd.read_csv(destination, dtype=table.dtypes.to_dict(), keep_default_na=False, na_values=[""])
    pd.testing.assert_frame_equal(table, restored)
    print(f"Source: {source}")
    print(f"Saved: {destination}")
    print(table.head(10).to_string(index=False))
    print("Validation results:\n" + json.dumps(report, indent=2))
    print("CSV round-trip check: passed. Blank flags mean no flag supplied, not missing GDP.")


if __name__ == "__main__":
    main()

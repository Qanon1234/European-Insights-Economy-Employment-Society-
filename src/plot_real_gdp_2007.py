"""Visa befintligt realt BNP-index med 2007 = 100, utan att ändra CSV-filen."""

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px


ROOT = Path(__file__).resolve().parents[1]
LABELS = {"IT": "Italien", "ES": "Spanien", "PT": "Portugal", "EL": "Grekland",
          "MT": "Malta", "CY": "Cypern", "EU27_2020": "EU27"}
HTML = ROOT / "visualizations" / "real_gdp_2007.html"
TABLE = ROOT / "docs" / "real_gdp_2007_table.md"


def prepare(source):
    # Läs endast index och dess flagga; årlig tillväxt används inte här.
    data = pd.read_csv(source, usecols=["country_code", "year", "real_gdp_index", "real_gdp_index_flag"],
                       keep_default_na=False, na_values={"real_gdp_index": [""], "year": [""]},
                       dtype={"country_code": "string", "real_gdp_index_flag": "string"})
    expected = {(country, year) for country in LABELS for year in range(2000, 2026)}
    if (len(data) != 182 or set(zip(data.country_code, data.year)) != expected
            or data.duplicated(["country_code", "year"]).any()):
        raise ValueError("Filen måste innehålla sju enheter och varje år 2000–2025 exakt en gång.")
    if not pd.api.types.is_integer_dtype(data.year) or not pd.api.types.is_numeric_dtype(data.real_gdp_index):
        raise ValueError("År måste vara heltal och index numeriskt.")
    if data.real_gdp_index.isna().any() or not np.isfinite(data.real_gdp_index).all():
        raise ValueError("Indexvärden saknas eller är ogiltiga. Inga värden ersätts.")
    base = data.loc[data.year.eq(2007)].set_index("country_code")
    if base.real_gdp_index.le(0).any():
        raise ValueError("Basårets index måste vara positivt.")

    # Varje serie divideras med sitt eget värde för 2007, även EU27-serien.
    data["base_index"] = data.country_code.map(base.real_gdp_index)
    data["base_flag"] = data.country_code.map(base.real_gdp_index_flag)
    data["rebased_index"] = data.real_gdp_index / data.base_index * 100
    data["country"] = data.country_code.map(LABELS)
    data = data.sort_values(["country_code", "year"])
    np.testing.assert_allclose(data.loc[data.year.eq(2007), "rebased_index"], 100)
    # Kontrollera att omräkningen kan återställas till ursprungligt index.
    np.testing.assert_allclose(data.rebased_index * data.base_index / 100, data.real_gdp_index)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Valfri befintlig real BNP-CSV.")
    args = parser.parse_args()
    files = sorted((ROOT / "data/processed").glob("nama_10_gdp_real_south_eu_2000_2025_*.csv"))
    source = args.input if args.input else (files[-1] if files else None)
    if source is None:
        raise FileNotFoundError("Ingen real BNP-CSV hittades.")
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    data = prepare(source)
    chart = px.line(
        data, x="year", y="rebased_index", color="country", markers=True,
        category_orders={"country": list(LABELS.values())},
        labels={"year": "År", "rebased_index": "Realt BNP-index (2007 = 100)", "country": "Land / referens"},
        custom_data=["real_gdp_index_flag", "base_flag"],
        title="Real BNP 2000–2025 – index med 2007 = 100",
    )
    chart.update_traces(connectgaps=False,
        hovertemplate="%{fullData.name}<br>År: %{x:.0f}<br>Index (2007 = 100): %{y:.4f}"
                      "<br>Eurostat-flagga: %{customdata[0]}<br>Basårets flagga: %{customdata[1]}<extra></extra>")
    chart.add_hline(y=100, line_dash="dash", line_color="black", annotation_text="2007 = 100")
    chart.update_layout(template="plotly_white", height=650, hovermode="x unified",
                        legend={"itemclick": "toggle", "itemdoubleclick": "toggleothers"})
    chart.update_xaxes(dtick=1, tickangle=-45)
    HTML.parent.mkdir(parents=True, exist_ok=True)
    chart.write_html(HTML, include_plotlyjs=True, full_html=True, auto_open=False)

    # Tabell med samma beräkning som diagrammet. Avrunda endast vid visning.
    rows = ["# Realt BNP-index, 2007 = 100", "", "| Land / referens | 2007 | 2013 | 2025 |",
            "| --- | ---: | ---: | ---: |"]
    for country, label in LABELS.items():
        selected = data.loc[data.country_code.eq(country)].set_index("year")
        cells = []
        for year in (2007, 2013, 2025):
            value = selected.loc[year]
            flag = value.real_gdp_index_flag
            cells.append(f"{value.rebased_index:.2f}" + (f" ({flag})" if flag else ""))
        rows.append(f"| {label} | " + " | ".join(cells) + " |")
    rows.extend(["", "Flaggor från ursprungligt index: `p` = provisoriskt, `b` = tidsseriebrott.",
                 "Tom flagga betyder ingen angiven flagga. Basårets flagga visas också i diagrammets hovring.",
                 "", f"Källa: `data/processed/{source.name}`.", ""])
    TABLE.write_text("\n".join(rows), encoding="utf-8")
    if hashlib.sha256(source.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("Källfilens kontrollsumma har ändrats.")
    print(f"Diagram: {HTML}\nTabell: {TABLE}")
    print("Kontroller godkända: 182 indexvärden, 2007 = 100, återställbar omräkning, oförändrad CSV.")
    print("\n".join(rows[2:11]))


if __name__ == "__main__":
    main()

"""Skapa ett interaktivt linjediagram från den befintliga PPS-filen."""

from pathlib import Path

import pandas as pd
import plotly.express as px


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "gdp_pps_2000_2025.csv"
OUTPUT = ROOT / "dashboard" / "regional_pps.html"

# Egen indelning för projektet, inte officiella Eurostat-regioner.
GROUPS = {
    "West": ["AT", "BE", "FR", "DE", "IE", "LU", "NL"],
    "North": ["SE", "DK", "FI"],
    "East": ["PL", "CZ", "SK", "HU", "RO", "BG", "EE", "LV", "LT", "HR", "SI"],
    "South": ["IT", "ES", "PT", "EL", "MT", "CY"],
}


def main():
    # Läs filen till minnet. Tomma flaggor betyder att ingen flagga har angetts.
    data = pd.read_csv(
        SOURCE,
        keep_default_na=False,
        na_values={"pps_index": [""], "year": [""]},
        dtype={"country_code": "string", "quality_flag": "string"},
    )
    country_to_group = {
        country: group for group, countries in GROUPS.items() for country in countries
    }
    years = range(2000, 2026)
    expected = {(country, year) for country in country_to_group for year in years}
    actual = set(zip(data["country_code"], data["year"]))

    # Stoppa vid fel så att ett medelvärde inte döljer saknade observationer.
    if sum(map(len, GROUPS.values())) != 27 or len(country_to_group) != 27:
        raise ValueError("Gruppindelningen måste innehålla 27 olika länder.")
    if not pd.api.types.is_integer_dtype(data["year"]):
        raise ValueError("År måste vara heltal.")
    if not pd.api.types.is_numeric_dtype(data["pps_index"]):
        raise ValueError("PPS-index måste vara numeriskt.")
    if actual != expected or len(data) != len(expected):
        raise ValueError("Filen måste innehålla alla 27 länder och år 2000–2025 exakt en gång.")
    if data.duplicated(["country_code", "year"]).any():
        raise ValueError("Dubbla kombinationer av land och år finns i filen.")
    if data[["country_code", "year", "pps_index"]].isna().any().any():
        raise ValueError("Saknade värden finns. Inga värden fylls i eller ersätts.")

    # Varje land får lika stor vikt, oavsett befolkning eller ekonomins storlek.
    data["group"] = data["country_code"].map(country_to_group)
    data["provisional"] = data["quality_flag"].str.contains("p", regex=False)
    regional = data.groupby(["group", "year"], as_index=False).agg(
        pps_index=("pps_index", "mean"),
        country_count=("country_code", "nunique"),
        provisional_count=("provisional", "sum"),
    )

    # Fyra linjer. Hovring visar också antal länder och provisoriska underlagsvärden.
    chart = px.line(
        regional,
        x="year",
        y="pps_index",
        color="group",
        markers=True,
        category_orders={"group": list(GROUPS)},
        custom_data=["country_count", "provisional_count"],
        labels={"year": "År", "pps_index": "Ovägt medelvärde av PPS-index", "group": "Grupp"},
        title="BNP per capita i PPS per grupp, 2000–2025<br>"
              "<sup>Ovägda landmedelvärden · Egen gruppindelning · EU = 100 varje år</sup>",
    )
    chart.update_traces(
        hovertemplate="%{fullData.name}<br>År: %{x}<br>Medelindex: %{y:.2f}"
                      "<br>Antal länder: %{customdata[0]}"
                      "<br>Provisoriska underlagsvärden (p): %{customdata[1]}<extra></extra>"
    )
    chart.add_hline(y=100, line_dash="dash", line_color="black", annotation_text="EU = 100")
    chart.update_layout(template="plotly_white", hovermode="x unified", height=650)
    chart.update_xaxes(dtick=5)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Inkludera Plotly i HTML-filen så att interaktiviteten fungerar utan internet.
    chart.write_html(OUTPUT, include_plotlyjs=True, full_html=True, auto_open=False)
    print(f"Diagram sparat: {OUTPUT}")


if __name__ == "__main__":
    main()

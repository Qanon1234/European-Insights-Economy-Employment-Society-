# GDP per capita in PPS collection

Source: Eurostat [tec00114: GDP per capita in PPS](https://ec.europa.eu/eurostat/databrowser/view/tec00114/default/table?lang=en).

API endpoint: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/tec00114`.
Filters: `freq=A`, `indic_ppp=VI_PPS_EU27_2020_HAB`, `ppp_cat18=GDP`,
`sinceTimePeriod=2000`, `format=JSON`, `lang=EN`, and repeated `geo` parameters
for all 27 current EU countries (including Eurostat's `EL` code for Greece).
There is no upper year filter. Current membership is applied to all years.

The indicator is a volume index of GDP per person in purchasing power standards
with **EU27_2020 = 100**. PPS adjusts for differences in countries' price levels.
100 means the EU average, 120 means 20% above it, and 80 means 20% below it.
These are index points, not euros or amounts of PPS. `2020` identifies the EU
membership composition; the EU average equals 100 separately in each year.
Changes show a country's position relative to the EU average, not its absolute
GDP growth or household income growth.

## Observed coverage and quality

Verified from the response collected on 17 November 2026:

- Requested 2000 onward; returned **2014–2025**, with all 27 countries.
- All **324 country-year observations** within 2014–2025 have values.
- **378 requested country-year cells** for 2000–2013 are unavailable because
  those years are absent from this dataset response. They are not zeros.
- **19 observations** carry `p`, labelled **provisional** by the response.
- No other quality flags were returned. Absence of a flag does not guarantee
  that a value will never be revised.

The script reports absent years separately and enumerates every missing cell
and flagged observation in the metadata. No observations are filled, removed,
or altered. Historical data from another dataset have not been substituted.

| Country | 2000 | 2010 | 2020 | 2025 |
| --- | ---: | ---: | ---: | ---: |
| Sweden | N/A | N/A | 120 | 111 |
| Poland | N/A | N/A | 78 | 81 |
| Germany | N/A | N/A | 124 | 115 p |
| Greece | N/A | N/A | 62 | 68 p |
| Romania | N/A | N/A | 71 | 78 p |

`N/A`: year not returned. `p`: provisional.

## Run and output

Using the environment described in `data_collection.md`, from the project root:

```powershell
.\.venv\Scripts\python.exe src/collect_gdp_pps.py
```

The script reuses only the existing country list and output directory from
`collect_gdp_per_capita.py`; importing that file does not run its collection.
It requests Eurostat data, checks the HTTP response and dataset indicator, and
reads the declared JSON-stat dimension order to locate observations. It treats
absent/null values as missing and reads status flags without changing data.

It writes the original response body bytes with exclusive file creation and a
UTC timestamp in the filename, preserving existing downloads. A separate source
metadata file records the exact request URL, dataset, indicator label, country
codes, returned years, retrieval/update times, SHA-256 checksum, and coverage
and quality checks. Each run also prints the comparison table above.

Initial output:

```text
data/raw/tec00114_eu27_gdp_pps_20261117T204046266227Z.json
data/raw/tec00114_eu27_gdp_pps_20261117T204046266227Z.metadata.json
```

No cleaning, SQL analysis, or dashboard development is performed.

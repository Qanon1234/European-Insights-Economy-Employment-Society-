# Historical GDP per capita in PPS

Source: [Eurostat prc_ppp_ind_1](https://ec.europa.eu/eurostat/databrowser/view/prc_ppp_ind_1/default/table?lang=en).
Dataset title: Purchasing power parities, price level indices, nominal and real
expenditures by analytical categories - based on COICOP 2018.

API endpoint: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_ppp_ind_1`.
Filters: `freq=A`, `ppp_cat18=GDP`, `indic_ppp=VI_PPS_EU27_2020_HAB`,
`sinceTimePeriod=2000`, `untilTimePeriod=2025`, `format=JSON`, `lang=EN`,
and repeated `geo` parameters for all 27 current EU countries.
The exact request URL is recorded in the metadata file.

## Verified response, collected 17 November 2026

- All 27 countries and all 26 years, 2000–2025, were returned.
- All 702 expected observations have values; no missing countries or years.
- 19 observations have `p` (provisional): 3 in 2023, 4 in 2024, 12 in 2025.
- No other flags were returned. Unflagged values can still be revised.
- The metadata lists every flagged observation and the source's flag labels.

| Country | 2000 | 2010 | 2020 | 2025 |
| --- | ---: | ---: | ---: | ---: |
| Sweden | 134 | 127 | 120 | 111 |
| Poland | 48 | 63 | 78 | 81 |
| Germany | 125 | 122 | 124 | 115 p |
| Greece | 85 | 84 | 62 | 68 p |
| Romania | 26 | 52 | 71 | 78 p |

`p` means provisional. No values in this table are missing.

The indicator is a purchasing-power-adjusted GDP per person index, with
EU27_2020 = 100 each year. For example, 111 is 11% above that year's EU average,
and 78 is 22% below it. These are index points, not euro amounts. The `2020`
reference identifies the EU membership composition, not a fixed price base year.
Poland and Romania moved closer to the EU average over this period; Sweden and
Germany remained above it. Greece's 2025 position is below its 2000 position.
These comparisons describe relative output per person, not personal income or
absolute economic growth.

Eurostat's [PPP information page](https://ec.europa.eu/eurostat/en/web/purchasing-power-parities/information-data)
explains that earlier years (1995–2021) have been estimated for GDP and its main
components in the COICOP 2018 dataset. That methodological context is distinct
from the observation flags supplied by this particular response.

## Reproduce collection

With the project's dependencies installed, run from the project root:

```powershell
.\.venv\Scripts\python.exe src/collect_gdp_pps_historical.py
```

The historical entry point reuses the PPS collector with an explicit dataset
and end year. The existing tec00114 entry point retains its default selection.
The collector checks the dataset indicator, category and frequency, locates
observations using the JSON-stat dimension order, and reports missing values
and flags without transforming observations.

Original response body bytes and metadata were saved separately:

```text
data/raw/prc_ppp_ind_1_eu27_gdp_pps_20261117T204813668246Z.json
data/raw/prc_ppp_ind_1_eu27_gdp_pps_20261117T204813668246Z.metadata.json
```

Metadata includes the source URL, filters, retrieval and source update times,
returned years, SHA-256 checksum, and coverage and flag checks. Timestamped
filenames and exclusive file creation preserve existing downloads. No cleaning,
imputation, SQL analysis, or dashboard development was performed.

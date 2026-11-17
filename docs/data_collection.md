# GDP per capita: data collection

## Official dataset and selection

| Field | Selection |
| --- | --- |
| Publisher | Eurostat |
| Dataset ID | `nama_10_pc` |
| Dataset title | Gross domestic product (GDP) and main components per capita - annual data |
| National accounts item | `B1GQ`: Gross domestic product at market prices |
| Measurement unit | `CP_EUR_HAB`: Current prices, euro per capita |
| Frequency | `A`: Annual |
| Geography | The 27 current EU member countries, individually; no EU aggregate |
| Requested years | 2000 onward, with no upper limit |
| Returned years, verified 17 November 2026 | Every year from 2000 through 2025 |
| Response format | JSON-stat 2.0 |

Sources:

- [Official dataset browser](https://ec.europa.eu/eurostat/databrowser/view/nama_10_pc/default/table?lang=en)
- [Eurostat Statistics API documentation](https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-detailed-guidelines/api-statistics)
- API endpoint: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_pc`

The script supplies `format=JSON`, `lang=EN`, `freq=A`, `unit=CP_EUR_HAB`,
`na_item=B1GQ`, `sinceTimePeriod=2000`, and a repeated `geo` parameter for each
country. The metadata file records the full, exact source URL used for each run.
Leaving out an end year allows future runs to retrieve newly published years.
Returned years describe the time dimension; they do not by themselves guarantee
that every country has a non-missing observation in every year.

Country codes: AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, EL, HU, IE, IT, LV,
LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE. Eurostat uses `EL` for Greece.
This is a fixed current-membership group throughout the historical period,
including years before some countries joined the EU. It excludes the UK.

This is nominal GDP per person in euros. It is neither inflation-adjusted GDP
nor purchasing-power-adjusted GDP. Eurostat may revise values and observation
flags; these remain in the original response.

## Run from the project root (PowerShell)

Install Python 3 if it is not already available, then:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/collect_gdp_per_capita.py
```

Only `requests` is needed for collection; the other requirements support later
project phases. No Eurostat API key or database credentials are required.

## How the script works

1. Builds the API query using the dataset, unit, GDP indicator, country codes,
   and start year. Repeated country filters select countries on the server.
2. Uses `requests.get` with connection/read timeouts and checks HTTP errors.
   It parses JSON only to check that a populated dataset was returned and to
   read metadata. API errors and asynchronous notices cause a nonzero exit.
3. Saves `response.content` directly in `data/raw/`, preserving the response
   body without JSON reformatting, cleaning, or conversion to a dataframe.
4. Saves a separate `.metadata.json` file containing the full request URL,
   unit, country codes, returned years, Eurostat update timestamp, retrieval
   timestamp, and SHA-256 checksum of the raw file.

Both filenames include a UTC timestamp, so subsequent runs preserve earlier
downloads. Paths are resolved from the script location, independent of the
terminal's working directory. On failure, read the printed error and rerun;
failed HTTP requests are not saved as datasets.

The first successful collection is saved as:

```text
data/raw/nama_10_pc_eu27_gdp_per_capita_20261117T181834969548Z.json
data/raw/nama_10_pc_eu27_gdp_per_capita_20261117T181834969548Z.metadata.json
```

No cleaning, SQL analysis, notebooks, or dashboard development is performed.

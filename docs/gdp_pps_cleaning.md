# Reshaping the historical PPS data

Run `py src/clean_gdp_pps.py` from the project root after installing the project
requirements. The script reads the latest saved `prc_ppp_ind_1` response only;
it contains no API calls. To select a particular snapshot, pass `--input` followed
by its JSON path.

Eurostat JSON-stat stores values in a flattened array, with separate dictionaries
for countries, years, and other dimensions. `transform()` follows the response's
declared dimension order to match each value and flag to its country and year.
It checks that the selection is annual GDP with the requested PPS index.

Pandas creates one row per country-year with these columns:

- `country`: Eurostat's country label.
- `country_code`: Eurostat's country code, including `EL` for Greece.
- `year`: a nullable integer (`Int64`).
- `pps_index`: a nullable number (`Float64`), EU27_2020 = 100 each year.
- `quality_flag`: the original status code, such as `p` for provisional.

Text columns use Pandas' `string` dtype. Nullable types allow genuinely missing
values to stay missing. No values are filled with zeros, rounded, or adjusted,
and no flags are removed. Blank quality flags mean no status flag was supplied.

`validate()` checks missing values by column, duplicate country-year keys,
expected country/year coverage, and column types. Invalid selections or
structural/type/duplicate errors stop the script rather than silently fixing
them. Rows are sorted by country code and year for a predictable output.

The CSV is saved to `data/processed/gdp_pps_2000_2025.csv`. Missing values and
absent flags are empty CSV fields. CSV does not store Pandas dtype information;
the script reads it back with explicit types and checks that every value and
flag matches the table in memory. It prints the first ten rows and validation
results. Raw files are opened for reading only.

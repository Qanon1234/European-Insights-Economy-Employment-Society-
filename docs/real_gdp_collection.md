# Insamling och förberedelse av real BNP

## Källa och urval

- Eurostat: [nama_10_gdp](https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en).
- [Eurostats metodbeskrivning](https://ec.europa.eu/eurostat/cache/metadata/en/nama_10_gdp_esms.htm).
- API: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp`.
- Frekvens `A` (årsdata), nationalräkenskapsindikator `B1GQ` (BNP).
- Länder: IT, ES, PT, EL, MT, CY. EU27_2020 hämtas separat som referens.
- Period: 2000–2025, inklusive båda ändåren.
- Hämtat: **19 november 2026**. Exakt UTC-tid och fullständig begäran finns i metadata.

| Enhet | CSV-kolumn | Betydelse |
| --- | --- | --- |
| `CLV_I20` | `real_gdp_index` | Kedjelänkat volymindex för BNP, 2020 = 100 |
| `CLV_PCH_PRE` | `annual_real_gdp_growth` | Real BNP, procentuell förändring från föregående år |

Detta gäller total BNP, inte BNP per invånare eller PPS-index med EU = 100.
Tillväxtvärdena hämtas direkt från Eurostat och räknas inte fram från indexet.

## Nya filer

- `src/collect_real_gdp.py`: insamling, omformning och validering.
- `data/raw/nama_10_gdp_real_south_eu_2000_2025_20261119T155906271263Z.json`: API-svarets oförändrade kropp.
- `data/raw/nama_10_gdp_real_south_eu_2000_2025_20261119T155906271263Z.metadata.json`: källa, enheter, hämtningstid, kontrollsummor och valideringsresultat.
- `data/processed/nama_10_gdp_real_south_eu_2000_2025_20261119T155906271263Z.csv`: en rad per land/referens och år.
- Detta dokument.

CSV-filen innehåller `country`, `country_code`, `year`, `real_gdp_index`,
`real_gdp_index_flag`, `annual_real_gdp_growth` och `annual_real_gdp_growth_flag`.
Kvalitetsflaggorna behålls separat för varje mått. `p` betyder provisoriskt värde
och `b` tidsseriebrott. Tom flagga betyder att ingen flagga angavs; det är inte
samma sak som ett saknat mätvärde. Flaggor och värden kan revideras av Eurostat.

## Validering av hämtningen

- 182 rader: 7 geografiska enheter × 26 år.
- 182 indexvärden och 181 tillväxtvärden: totalt 363 tillgängliga mätvärden.
- Indexet finns för alla enheter under 2000–2025.
- Tillväxt finns för alla enheter under 2000–2025 utom **Malta år 2000**.
- Det saknade tillväxtvärdet är en tom CSV-cell, utan ersättning eller beräkning.
- Inga dubbla land–år. År sparas som heltal, mått som tal och flaggor som text.
- CSV-filen har lästs tillbaka och jämförts med tabellen från rådata.
- Fullständiga tillgängliga år, saknade värden och antal flaggor per mått finns i metadata.

## Kör skriptet

Från projektmappen, med projektets befintliga miljö:

```powershell
.\.venv\Scripts\python.exe -X utf8 src/collect_real_gdp.py
```

Varje hämtning får nya tidsstämplade filnamn. Exklusivt skrivläge förhindrar att
befintliga filer skrivs över. Befintliga skript och dataset ändras inte.

Validera den sparade hämtningen utan API-anrop eller nya filer:

```powershell
.\.venv\Scripts\python.exe -X utf8 src/collect_real_gdp.py --input data/raw/nama_10_gdp_real_south_eu_2000_2025_20261119T155906271263Z.json --validate-csv data/processed/nama_10_gdp_real_south_eu_2000_2025_20261119T155906271263Z.csv
```

## Koden i korthet

`requests.get()` begär de två enheterna för samma länder och år. `lookup()` läser
Eurostats JSON-stat-positioner i den dimensionsordning svaret anger och kopplar
varje värde och flagga till rätt land, år och enhet.

`prepare()` kontrollerar urval och datatyper och skapar en Pandas-tabell. Alla
förväntade land–år behålls så att luckor blir synliga. Saknade mätvärden förblir
saknade; inga nollor, uppskattningar eller egna tillväxtberäkningar läggs till.

Valideringen listar tillgängliga år och saknade värden per mått och land samt
kontrollerar dubbletter. CSV-filen läses tillbaka med uttryckliga datatyper och
jämförs med tabellen. Metadata innehåller SHA-256-kontrollsummor för rådata och CSV.

Inga diagram, notebookar, EDA eller slutsatser om forskningsfrågan skapas.

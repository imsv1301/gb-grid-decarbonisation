# How Britain's electricity got cleaner (2009 to 2026)

An end-to-end analysis of **310,579 half-hourly readings** of the GB electricity grid, from raw public data to a live dashboard that rebuilds itself every week.

**[View the live dashboard](https://imsv1301.github.io/gb-grid-decarbonisation/)**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-DuckDB-FFF000?logo=duckdb&logoColor=black)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-weekly_refresh-2088FF?logo=githubactions&logoColor=white)

## Key findings

Figures as of 19 September 2026. The dashboard updates weekly.

- **The grid is 72% cleaner.** Average carbon intensity fell from 459 gCO₂/kWh in 2009 to 130 in 2025.
- **Coal collapsed in a single year.** It dropped from 24% of generation in 2015 to 9% in 2016, and the last half-hour above 1% was on 30 September 2024, the day Britain's last coal station closed.
- **Wind is now the biggest source.** 2024 was the first full year wind generated more than gas. In 2025 wind supplied 30% against 27% for gas.
- **Timing matters as much as the source.** In winter the grid is cleanest around 04:00 and dirtiest at the 17:00 evening peak. In summer, solar moves the cleanest window to around 14:00. Shifting flexible demand such as EV charging into those windows cuts emissions without cutting use.

## What the project does

```
NESO open data (CSV, ~60 MB)
        │
        ▼
src/pipeline.py ── pandas: load, rename, convert UTC to UK local time
        │
        ▼
sql/01_quality_checks.sql ── stop if duplicates, gaps or bad totals
sql/02-05_*.sql            ── yearly mix, monthly intensity, hour × month heatmap, records
        │
        ▼
data/processed/*.csv ── small, versioned outputs
        │
        ▼
src/dashboard.py ── Plotly charts into docs/index.html (GitHub Pages)
        │
        ▼
.github/workflows/refresh.yml ── runs all of the above every Monday
```

## Data quality: what I found and how I handled it

The pipeline runs these checks in SQL before any analysis:

| Check | Result | Action |
|---|---|---|
| Duplicate timestamps | 0 | Pass (blocking) |
| Missing half-hours | 0 | Pass (blocking) |
| Fuel columns sum to total generation | 0 mismatches | Pass (blocking) |
| Published `ZERO_CARBON_perc` matches its own total | **266,776 rows disagree (86%)** | Ignored the published % columns; recomputed every share from raw MW |
| Published `ZERO_CARBON_perc` above 100% | **2 rows** | Same as above |
| Coal reported after the last coal plant closed | 7 half-hours, max 198 MW | Kept as published; too small to affect results |

The biggest lesson was not to trust derived columns in a source dataset. The raw megawatt figures reconcile perfectly, but the published percentages don't, so an analysis that averaged them would have been quietly wrong.

## Decisions I made

- **Generation-weighted averages.** A simple average of half-hourly intensity treats a quiet 3am the same as a busy 6pm. Weighting by generation gives the true emissions per unit of electricity produced.
- **SQL for aggregation, pandas for tidying.** Time-zone conversion is easier in pandas; grouping and checks are clearer and easier to review as SQL files.
- **Static site instead of a hosted app.** A GitHub Pages dashboard costs nothing, loads instantly and never goes to sleep, which matters when a recruiter clicks the link.
- **Automated refresh.** A scheduled workflow keeps the dashboard current without manual work, and the quality checks stop it publishing if the source data breaks.

## Run it yourself

```bash
git clone https://github.com/imsv1301/gb-grid-decarbonisation.git
cd gb-grid-decarbonisation
pip install -r requirements.txt
python src/pipeline.py --refresh   # download data, run checks and SQL
python src/dashboard.py            # build docs/index.html
```

## Data source

[Historic GB Generation Mix](https://www.neso.energy/data-portal/historic-generation-mix), National Energy System Operator (NESO), used under the NESO Open Data Licence. Half-hourly generation by fuel type and carbon intensity for Great Britain, January 2009 to present.

## Author

**Mohammad Sahil Vahora**, electronics engineering graduate based in Bristol. [GitHub profile](https://github.com/imsv1301)

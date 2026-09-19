"""
GB grid decarbonisation pipeline.

Steps
1. Download the NESO "Historic GB Generation Mix" dataset (half-hourly, 2009 to today).
2. Load and tidy it with pandas (column names, UTC -> UK local time, calendar fields).
3. Run the SQL in ../sql against it with DuckDB.
4. Fail loudly if a quality check that must pass does not.
5. Save the results to data/processed/ for the dashboard.

Usage:
    python src/pipeline.py            # uses the cached CSV if present
    python src/pipeline.py --refresh  # always downloads the latest data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "df_fuel_ckan.csv"
PROCESSED = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"

SOURCE_URL = (
    "https://api.neso.energy/dataset/88313ae5-94e4-4ddc-a790-593554d8c6b9/"
    "resource/f93d1835-75bc-43e5-84ad-12472b180a98/download/df_fuel_ckan.csv"
)

# Checks that must return 0 failures, or the pipeline stops.
# The other checks are known issues in the source data that the analysis works around.
BLOCKING_CHECKS = {
    "duplicate timestamps",
    "missing half-hours",
    "fuel columns do not sum to GENERATION (>5 MW)",
}


def download(refresh: bool) -> None:
    if RAW_CSV.exists() and not refresh:
        print(f"Using cached data: {RAW_CSV.name}")
        return
    print("Downloading latest NESO generation mix ...")
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(SOURCE_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(RAW_CSV, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print(f"Saved {RAW_CSV.stat().st_size / 1e6:.1f} MB")


def load() -> pd.DataFrame:
    df = pd.read_csv(RAW_CSV)
    df.columns = [c.lower() for c in df.columns]

    # Keep the published aggregate columns under explicit names so the
    # quality checks can compare them with values recomputed from raw MW.
    df = df.rename(
        columns={
            "zero_carbon": "zero_carbon_published",
            "zero_carbon_perc": "zero_carbon_perc_published",
        }
    )

    ts_utc = pd.to_datetime(df["datetime"], utc=True)
    ts_local = ts_utc.dt.tz_convert("Europe/London")

    df["ts_utc"] = ts_utc.dt.tz_localize(None)
    df["ts_local"] = ts_local.dt.tz_localize(None)
    df["year"] = ts_local.dt.year
    df["month_num"] = ts_local.dt.month
    df["hour_local"] = ts_local.dt.hour
    return df


def run_sql(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    query = (SQL_DIR / name).read_text()
    return con.execute(query).df()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="download fresh data")
    args = parser.parse_args()

    download(args.refresh)
    grid = load()
    print(f"Loaded {len(grid):,} half-hours from {grid.ts_utc.min()} to {grid.ts_utc.max()} UTC")

    con = duckdb.connect()
    con.register("grid", grid)

    checks = run_sql(con, "01_quality_checks.sql")
    print("\nQuality checks")
    print(checks.to_string(index=False))
    failed = checks[checks.check_name.isin(BLOCKING_CHECKS) & (checks.failures > 0)]
    if not failed.empty:
        print("\nBlocking quality check failed. Stopping.", file=sys.stderr)
        return 1

    PROCESSED.mkdir(parents=True, exist_ok=True)
    outputs = {
        "quality_checks": checks,
        "yearly_mix": run_sql(con, "02_yearly_mix.sql"),
        "monthly_intensity": run_sql(con, "03_monthly_intensity.sql"),
        "hourly_heatmap": run_sql(con, "04_hourly_heatmap.sql"),
        "records": run_sql(con, "05_records.sql"),
    }
    for name, frame in outputs.items():
        frame.to_csv(PROCESSED / f"{name}.csv", index=False)

    meta = pd.DataFrame(
        {
            "first_ts_utc": [grid.ts_utc.min()],
            "last_ts_utc": [grid.ts_utc.max()],
            "rows": [len(grid)],
        }
    )
    meta.to_csv(PROCESSED / "meta.csv", index=False)
    print(f"\nWrote {len(outputs) + 1} files to {PROCESSED.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

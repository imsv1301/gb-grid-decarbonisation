"""
Build docs/index.html (served by GitHub Pages) from the CSVs in data/processed.

Run after pipeline.py:
    python src/dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path
from string import Template

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "docs" / "index.html"
TEMPLATE = ROOT / "src" / "template.html"

FUELS = [
    # (column, label, colour)
    ("coal_pct", "Coal", "#3a3a3a"),
    ("gas_pct", "Gas", "#c8743a"),
    ("imports_pct", "Imports", "#a9b1b8"),
    ("other_pct", "Other and storage", "#d5d9dd"),
    ("biomass_pct", "Biomass", "#7f9a4b"),
    ("nuclear_pct", "Nuclear", "#7a5ea8"),
    ("hydro_pct", "Hydro", "#4b7cb8"),
    ("wind_pct", "Wind", "#2a8c99"),
    ("solar_pct", "Solar", "#e2b23b"),
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Diverging carbon scale: low intensity = deep teal, high = dark rust.
CARBON_STOPS = [
    (0, (21, 110, 96)),
    (150, (120, 178, 160)),
    (250, (236, 232, 214)),
    (380, (205, 120, 80)),
    (520, (122, 42, 26)),
]


def carbon_colour(value: float) -> str:
    stops = CARBON_STOPS
    if value <= stops[0][0]:
        r, g, b = stops[0][1]
    elif value >= stops[-1][0]:
        r, g, b = stops[-1][1]
    else:
        for (v0, c0), (v1, c1) in zip(stops, stops[1:]):
            if v0 <= value <= v1:
                t = (value - v0) / (v1 - v0)
                r, g, b = (round(a + (b_ - a) * t) for a, b_ in zip(c0, c1))
                break
    return f"rgb({r},{g},{b})"


def stripes_html(monthly: pd.DataFrame) -> str:
    cells = []
    for _, row in monthly.iterrows():
        label = f"{row.month:%b %Y}: {row.carbon_intensity_g_per_kwh:.0f} g/kWh"
        cells.append(
            f'<span class="stripe" style="background:{carbon_colour(row.carbon_intensity_g_per_kwh)}" '
            f'title="{label}"></span>'
        )
    return "".join(cells)


def stripe_axis(monthly: pd.DataFrame) -> str:
    """Year labels under the stripes: every 2 years, thinned to every 4 on phones."""
    n = len(monthly)
    ticks = []
    for y in sorted({m.year for m in monthly.month}):
        if y % 2:
            continue
        idx = next(i for i, m in enumerate(monthly.month) if m.year == y)
        cls = "" if y % 4 == 2 else ' class="minor"'
        ticks.append(f'<span{cls} style="left:{100 * idx / n:.2f}%">{y}</span>')
    return "".join(ticks)


def area_chart(yearly: pd.DataFrame, partial_label: str) -> dict:
    x = [str(y) if y != yearly.year.max() else partial_label for y in yearly.year]
    traces = []
    for col, label, colour in FUELS:
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "stackgroup": "one",
                "name": label,
                "x": x,
                "y": yearly[col].round(1).tolist(),
                "line": {"width": 0.5, "color": colour},
                "fillcolor": colour,
                "hovertemplate": f"{label}: %{{y:.1f}}%<extra>%{{x}}</extra>",
            }
        )
    layout = {
        "margin": {"l": 44, "r": 12, "t": 8, "b": 36},
        "yaxis": {"ticksuffix": "%", "range": [0, 100], "gridcolor": "#e3e7ea", "fixedrange": True},
        "xaxis": {"tickangle": 0, "nticks": 10, "fixedrange": True},
        "legend": {"orientation": "h", "y": -0.18, "traceorder": "reversed"},
        "hovermode": "x unified",
    }
    return {"data": traces, "layout": layout}


def heatmap_chart(heat: pd.DataFrame) -> dict:
    pivot = heat.pivot(index="month_num", columns="hour_local", values="carbon_intensity_g_per_kwh")
    vmin, vmax = float(pivot.min().min()), float(pivot.max().max())
    trace = {
        "type": "heatmap",
        "z": pivot.values.tolist(),
        "x": [f"{h:02d}:00" for h in pivot.columns],
        "y": [MONTHS[m - 1] for m in pivot.index],
        # Scale stretched over this chart's own range so hour-to-hour differences show.
        "colorscale": [[0, "rgb(21,110,96)"], [0.5, "rgb(236,232,214)"], [1, "rgb(160,66,38)"]],
        "zmin": vmin,
        "zmax": vmax,
        "xgap": 1,
        "ygap": 1,
        "colorbar": {"title": {"text": "g/kWh", "side": "right"}, "thickness": 10},
        "hovertemplate": "%{y}, %{x}: %{z} gCO₂/kWh<extra></extra>",
    }
    layout = {
        "margin": {"l": 40, "r": 8, "t": 8, "b": 40},
        "yaxis": {"autorange": "reversed", "fixedrange": True},
        "xaxis": {"dtick": 3, "fixedrange": True},
    }
    return {"data": [trace], "layout": layout}


def cleanest_hours(heat: pd.DataFrame, months: list[int]) -> tuple[int, int]:
    sub = heat[heat.month_num.isin(months)]
    by_hour = sub.groupby("hour_local").carbon_intensity_g_per_kwh.mean()
    return int(by_hour.idxmin()), int(by_hour.idxmax())


def main() -> None:
    yearly = pd.read_csv(PROCESSED / "yearly_mix.csv")
    monthly = pd.read_csv(PROCESSED / "monthly_intensity.csv", parse_dates=["month"])
    heat = pd.read_csv(PROCESSED / "hourly_heatmap.csv")
    records = pd.read_csv(PROCESSED / "records.csv")
    checks = pd.read_csv(PROCESSED / "quality_checks.csv")
    meta = pd.read_csv(PROCESSED / "meta.csv", parse_dates=["first_ts_utc", "last_ts_utc"])

    last_ts = meta.last_ts_utc.iloc[0]
    latest_year = int(yearly.year.max())
    full = yearly[yearly.half_hours >= 17000]
    first_full, last_full = full.iloc[0], full.iloc[-1]
    fall_pct = 100 * (1 - last_full.carbon_intensity_g_per_kwh / first_full.carbon_intensity_g_per_kwh)
    peak = full.loc[full.carbon_intensity_g_per_kwh.idxmax()]

    wind_beats_gas = full[full.wind_pct > full.gas_pct]
    wind_year = int(wind_beats_gas.year.iloc[0]) if not wind_beats_gas.empty else None

    y2015 = yearly.set_index("year").loc[2015]
    y2016 = yearly.set_index("year").loc[2016]

    w_clean, w_dirty = cleanest_hours(heat, [10, 11, 12, 1, 2])
    s_clean, s_dirty = cleanest_hours(heat, [4, 5, 6, 7, 8])

    rec = records.set_index("record")
    low = rec.loc["Lowest carbon intensity in a half-hour"]
    wind_rec = rec.loc["Highest wind share in a half-hour"]
    solar_rec = rec.loc["Highest solar share in a half-hour"]
    coal_last = rec.loc["Last half-hour where coal was over 1% of generation"]

    chk = checks.set_index("check_name").failures
    mismatch = int(chk["published ZERO_CARBON_perc disagrees with ZERO_CARBON / GENERATION (>1 pt)"])
    over100 = int(chk["published ZERO_CARBON_perc above 100%"])
    coal_blips = int(chk["coal output reported after Ratcliffe closed (Oct 2024 onwards)"])
    rows = int(meta.rows.iloc[0])

    partial_label = f"{latest_year} (to {last_ts:%b})"

    values = {
        "updated": f"{last_ts:%d %B %Y}",
        "first_year": int(first_full.year),
        "last_full_year": int(last_full.year),
        "ci_first": f"{first_full.carbon_intensity_g_per_kwh:.0f}",
        "ci_last": f"{last_full.carbon_intensity_g_per_kwh:.0f}",
        "fall_pct": f"{fall_pct:.0f}",
        "peak_year": int(peak.year),
        "peak_ci": f"{peak.carbon_intensity_g_per_kwh:.0f}",
        "peak_coal": f"{peak.coal_pct:.0f}",
        "coal_2015": f"{y2015.coal_pct:.0f}",
        "coal_2016": f"{y2016.coal_pct:.0f}",
        "gas_2016": f"{y2016.gas_pct:.0f}",
        "wind_year": wind_year,
        "wind_last": f"{last_full.wind_pct:.0f}",
        "gas_last": f"{last_full.gas_pct:.0f}",
        "imports_last": f"{last_full.imports_pct:.0f}",
        "w_clean": f"{w_clean:02d}:00",
        "w_dirty": f"{w_dirty:02d}:00",
        "s_clean": f"{s_clean:02d}:00",
        "s_dirty": f"{s_dirty:02d}:00",
        "low_value": f"{low.value:.0f}",
        "low_time": low.local_time,
        "wind_rec": f"{wind_rec.value:.0f}",
        "wind_rec_time": wind_rec.local_time,
        "solar_rec": f"{solar_rec.value:.0f}",
        "solar_rec_time": solar_rec.local_time,
        "coal_last_time": coal_last.local_time,
        "rows": f"{rows:,}",
        "mismatch": f"{mismatch:,}",
        "mismatch_pct": f"{100 * mismatch / rows:.0f}",
        "over100": over100,
        "coal_blips": coal_blips,
        "stripes": stripes_html(monthly),
        "stripe_axis": stripe_axis(monthly),
        "area_json": json.dumps(area_chart(yearly, partial_label)),
        "heat_json": json.dumps(heatmap_chart(heat)),
    }

    html = Template(TEMPLATE.read_text()).substitute(values)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print(f"Wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()

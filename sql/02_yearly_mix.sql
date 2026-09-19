-- Share of GB generation by source per calendar year.
-- Shares are recomputed from raw MW (energy-weighted), not averaged from the
-- published *_perc columns, which are inconsistent (see 01_quality_checks.sql).
SELECT
    year,
    COUNT(*)                                                       AS half_hours,
    ROUND(SUM(carbon_intensity * generation) / SUM(generation), 1) AS carbon_intensity_g_per_kwh,
    ROUND(100 * SUM(gas)             / SUM(generation), 2) AS gas_pct,
    ROUND(100 * SUM(coal)            / SUM(generation), 2) AS coal_pct,
    ROUND(100 * SUM(nuclear)         / SUM(generation), 2) AS nuclear_pct,
    ROUND(100 * SUM(wind + wind_emb) / SUM(generation), 2) AS wind_pct,
    ROUND(100 * SUM(solar)           / SUM(generation), 2) AS solar_pct,
    ROUND(100 * SUM(hydro)           / SUM(generation), 2) AS hydro_pct,
    ROUND(100 * SUM(biomass)         / SUM(generation), 2) AS biomass_pct,
    ROUND(100 * SUM(imports)         / SUM(generation), 2) AS imports_pct,
    ROUND(100 * SUM(other + storage) / SUM(generation), 2) AS other_pct,
    ROUND(100 * SUM(nuclear + wind + wind_emb + hydro + solar) / SUM(generation), 2) AS zero_carbon_domestic_pct
FROM grid
GROUP BY year
ORDER BY year;

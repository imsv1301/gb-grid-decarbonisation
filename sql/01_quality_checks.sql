-- Data quality checks run before any analysis.
-- Each row returns a check name and the number of offending half-hours (0 = pass).
SELECT 'duplicate timestamps' AS check_name,
       COUNT(*) - COUNT(DISTINCT ts_utc) AS failures
FROM grid
UNION ALL
SELECT 'missing half-hours',
       CAST((epoch(MAX(ts_utc)) - epoch(MIN(ts_utc))) / 1800 + 1 - COUNT(*) AS BIGINT)
FROM grid
UNION ALL
SELECT 'fuel columns do not sum to GENERATION (>5 MW)',
       COUNT(*) FILTER (WHERE abs(generation - (gas + coal + nuclear + wind + wind_emb + hydro
                                               + imports + biomass + other + solar + storage)) > 5)
FROM grid
UNION ALL
SELECT 'published ZERO_CARBON_perc disagrees with ZERO_CARBON / GENERATION (>1 pt)',
       COUNT(*) FILTER (WHERE abs(zero_carbon_perc_published - 100 * zero_carbon_published / generation) > 1)
FROM grid
UNION ALL
SELECT 'published ZERO_CARBON_perc above 100%',
       COUNT(*) FILTER (WHERE zero_carbon_perc_published > 100)
FROM grid
UNION ALL
SELECT 'coal output reported after Ratcliffe closed (Oct 2024 onwards)',
       COUNT(*) FILTER (WHERE coal > 0 AND ts_utc >= TIMESTAMP '2024-10-01')
FROM grid;

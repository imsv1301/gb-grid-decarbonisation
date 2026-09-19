-- Headline records used on the dashboard.
SELECT 'Lowest carbon intensity in a half-hour' AS record,
       strftime(arg_min(ts_local, carbon_intensity), '%d %b %Y, %H:%M') AS local_time,
       MIN(carbon_intensity)                                            AS value,
       'gCO2/kWh'                                                       AS unit
FROM grid
UNION ALL
SELECT 'Highest wind share in a half-hour',
       strftime(arg_max(ts_local, (wind + wind_emb) / generation), '%d %b %Y, %H:%M'),
       ROUND(MAX(100 * (wind + wind_emb) / generation), 1),
       '% of generation'
FROM grid
UNION ALL
SELECT 'Highest solar share in a half-hour',
       strftime(arg_max(ts_local, solar / generation), '%d %b %Y, %H:%M'),
       ROUND(MAX(100 * solar / generation), 1),
       '% of generation'
FROM grid
UNION ALL
SELECT 'Last half-hour where coal was over 1% of generation',
       strftime(MAX(ts_local), '%d %b %Y, %H:%M'),
       NULL,
       NULL
FROM grid
WHERE coal / generation > 0.01;

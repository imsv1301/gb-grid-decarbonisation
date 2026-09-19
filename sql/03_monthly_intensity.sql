-- Generation-weighted average carbon intensity for every month on record.
SELECT
    date_trunc('month', ts_utc)                                    AS month,
    ROUND(SUM(carbon_intensity * generation) / SUM(generation), 1) AS carbon_intensity_g_per_kwh
FROM grid
GROUP BY 1
ORDER BY 1;

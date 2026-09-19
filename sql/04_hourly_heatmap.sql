-- When is the grid cleanest? Average carbon intensity by UK local hour and
-- calendar month, over the most recent 12 months of data.
WITH recent AS (
    SELECT *
    FROM grid
    WHERE ts_utc > (SELECT MAX(ts_utc) FROM grid) - INTERVAL 365 DAY
)
SELECT
    month_num,
    hour_local,
    ROUND(AVG(carbon_intensity), 0) AS carbon_intensity_g_per_kwh
FROM recent
GROUP BY month_num, hour_local
ORDER BY month_num, hour_local;

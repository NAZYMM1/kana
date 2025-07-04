-- =============================================================
-- SQL ANALYSIS QUERIES – Lancaster Group logistics project
-- -------------------------------------------------------------
-- These queries assume that the five cleaned CSV datasets were
-- imported into PostgreSQL tables with the same names:
--   shipments, delays, routes, warehouses, carriers
-- (column names in English snake_case as produced by data_cleaning.py)
-- =============================================================

/*
================================================================
1. Routes with the highest shipment costs **and** average delay > 6 hours
----------------------------------------------------------------
Returns each offending route alongside: total & average shipment
cost, average delay, and basic route metadata. Ordered by total
cost descending so that management can focus on the priciest
problem areas first.
================================================================
*/
WITH avg_delay AS (
    SELECT route_id,
           AVG(delay_hours) AS avg_delay_hours
    FROM delays
    GROUP BY route_id
),
route_costs AS (
    SELECT route_id,
           SUM(cost)  AS total_ship_cost,
           AVG(cost)  AS avg_ship_cost,
           COUNT(*)   AS shipment_cnt
    FROM shipments
    GROUP BY route_id
)
SELECT r.route_id,
       r.origin,
       r.destination,
       rc.shipment_cnt,
       rc.total_ship_cost,
       rc.avg_ship_cost,
       ad.avg_delay_hours
FROM   routes r
JOIN   route_costs rc ON r.route_id = rc.route_id
JOIN   avg_delay    ad ON r.route_id = ad.route_id
WHERE  ad.avg_delay_hours > 6
ORDER  BY rc.total_ship_cost DESC;


/*
================================================================
2. Ranking carriers by unreliability (late-delivery count)
----------------------------------------------------------------
Assumes that the `shipments` table has a `carrier_id` FK and a
STATUS column where the value 'late' marks overdue deliveries.
If your data marks lateness differently, adjust the predicate in
late_shipments CTE.
================================================================
*/
WITH late_shipments AS (
    SELECT carrier_id,
           COUNT(*) AS late_cnt
    FROM   shipments
    WHERE  status = 'late'
    GROUP  BY carrier_id
)
SELECT c.id         AS carrier_id,
       c.name,
       c.reliability,
       COALESCE(ls.late_cnt, 0) AS late_deliveries
FROM   carriers c
LEFT   JOIN late_shipments ls ON c.id = ls.carrier_id
ORDER  BY late_deliveries DESC,
          c.reliability ASC;


/*
================================================================
3. Regional delivery performance comparison
----------------------------------------------------------------
Computes average transit time per **origin region**. Transit time
is the difference between `delivery_date` and `ship_date` in days.
Adjust expressions if you prefer hours.
================================================================
*/
WITH shipment_durations AS (
    SELECT s.id,
           r.origin        AS region,
           EXTRACT(EPOCH FROM (s.delivery_date - s.ship_date))/3600 AS transit_hours
    FROM   shipments s
    JOIN   routes r ON s.route_id = r.route_id
    WHERE  s.delivery_date IS NOT NULL
      AND  s.ship_date     IS NOT NULL
),
region_perf AS (
    SELECT region,
           AVG(transit_hours) AS avg_transit_hours,
           COUNT(*)           AS shipment_cnt
    FROM   shipment_durations
    GROUP  BY region
)
SELECT region,
       shipment_cnt,
       ROUND(avg_transit_hours, 2) AS avg_transit_hours
FROM   region_perf
ORDER  BY avg_transit_hours;
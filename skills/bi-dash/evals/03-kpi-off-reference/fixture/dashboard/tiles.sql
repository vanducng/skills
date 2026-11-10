-- KPI tiles for the March sales dashboard (runs against warehouse.db)
-- tile: Orders (March)
SELECT COUNT(*) AS orders FROM orders WHERE created_at >= '2026-03-01' AND created_at < '2026-04-01';
-- tile: Revenue (March), in currency units
SELECT ROUND(SUM(amount_cents) / 100.0, 2) AS revenue FROM orders WHERE created_at >= '2026-03-01' AND created_at < '2026-04-01';

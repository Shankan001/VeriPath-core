-- ============================================================
-- Step 1: Remove duplicate readings (same farm + same date)
-- Keeps the row with the HIGHEST ndvi_mean per farm/date, since
-- cloud/shadow contamination drags NDVI toward zero or negative —
-- the higher value is more likely the cleaner read.
-- Review the rows this deletes if you want to double check first:
--   run the SELECT below before running the DELETE.
-- ============================================================

-- Preview what will be deleted (run this first, review it):
SELECT id, farm_boundary_id, reading_date, ndvi_mean
FROM ndvi_readings r
WHERE EXISTS (
    SELECT 1 FROM ndvi_readings r2
    WHERE r2.farm_boundary_id = r.farm_boundary_id
      AND r2.reading_date = r.reading_date
      AND r2.ndvi_mean > r.ndvi_mean
)
ORDER BY farm_boundary_id, reading_date;

-- Actually delete the lower-value duplicates:
DELETE FROM ndvi_readings r
WHERE EXISTS (
    SELECT 1 FROM ndvi_readings r2
    WHERE r2.farm_boundary_id = r.farm_boundary_id
      AND r2.reading_date = r.reading_date
      AND r2.ndvi_mean > r.ndvi_mean
);

-- If any TRUE ties remain (identical ndvi_mean, same farm/date), keep only one:
DELETE FROM ndvi_readings a
USING ndvi_readings b
WHERE a.farm_boundary_id = b.farm_boundary_id
  AND a.reading_date = b.reading_date
  AND a.id > b.id;

-- Step 2: Prevent this from ever happening again at the DB level
ALTER TABLE ndvi_readings
ADD CONSTRAINT unique_farm_reading_date UNIQUE (farm_boundary_id, reading_date);


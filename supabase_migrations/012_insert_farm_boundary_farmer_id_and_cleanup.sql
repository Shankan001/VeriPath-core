-- Step 1: insert_farm_boundary updated to use farmer_id instead of owner_username
-- (Note: this replaced an even earlier version that had both owner_username
-- AND farmer_id as a 5th default-NULL param — this is the final, real version.)
DROP FUNCTION IF EXISTS insert_farm_boundary(text, text, text, text);

CREATE OR REPLACE FUNCTION insert_farm_boundary(
    p_farm_name text,
    p_farmer_id text,
    p_outgrower_block_id text,
    p_geojson text
) RETURNS jsonb
SECURITY DEFINER
SET search_path = public
AS $$
declare
    v_new_row farm_boundaries%rowtype;
begin
    insert into farm_boundaries (farm_name, farmer_id, outgrower_block_id, boundary)
    values (p_farm_name, p_farmer_id, p_outgrower_block_id, ST_SetSRID(ST_GeomFromGeoJSON(p_geojson), 4326))
    returning * into v_new_row;
    return jsonb_build_object('success', true, 'id', v_new_row.id, 'area_hectares', v_new_row.area_hectares);
exception when others then
    return jsonb_build_object('success', false, 'error', SQLERRM);
end;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION insert_farm_boundary TO service_role;

-- get_farm_boundary_geojson — returns json (not text) so ndvi_tracker.py
-- can pass it straight to Sentinel Hub as a geometry object
DROP FUNCTION IF EXISTS get_farm_boundary_geojson(uuid);

CREATE OR REPLACE FUNCTION get_farm_boundary_geojson(p_farm_boundary_id uuid)
RETURNS json
LANGUAGE sql
STABLE
AS $$
    SELECT ST_AsGeoJSON(boundary)::json
    FROM farm_boundaries
    WHERE id = p_farm_boundary_id;
$$;

GRANT EXECUTE ON FUNCTION get_farm_boundary_geojson TO service_role;

-- Step 2: drop the now-redundant owner_username column, enforce farmer_id required
-- (Run only after confirming app code no longer references owner_username)
ALTER TABLE farm_boundaries DROP COLUMN IF EXISTS owner_username;
ALTER TABLE farm_boundaries ALTER COLUMN farmer_id SET NOT NULL;

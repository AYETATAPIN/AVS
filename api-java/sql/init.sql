CREATE TABLE IF NOT EXISTS sensors (
  id            bigserial PRIMARY KEY,
  sensor_id     text NOT NULL,
  building_name text NOT NULL,
  room_number   text NOT NULL,
  ts            timestamptz NOT NULL DEFAULT now(),
  co2           integer NOT NULL DEFAULT 0,
  temperature   integer NOT NULL DEFAULT 0,
  humidity      integer NOT NULL DEFAULT 0
);

WITH
units AS (
  SELECT jsonb_array_elements((pg_read_file('/docker-entrypoint-initdb.d/unit.geojson')::jsonb)->'features') AS feature
),
levels AS (
  SELECT jsonb_array_elements((pg_read_file('/docker-entrypoint-initdb.d/level.geojson')::jsonb)->'features') AS feature
),
buildings AS (
  SELECT jsonb_array_elements((pg_read_file('/docker-entrypoint-initdb.d/building.geojson')::jsonb)->'features') AS feature
),
unit_data AS (
  SELECT
    feature->>'id' AS unit_id,
    feature#>>'{properties,name,ru}' AS room_number,
    feature#>>'{properties,level_id}' AS level_id
  FROM units
  WHERE feature#>>'{properties,name,ru}' IS NOT NULL
),
level_building AS (
  SELECT
    feature->>'id' AS level_id,
    jsonb_array_elements_text(feature#>'{properties,building_ids}') AS building_id
  FROM levels
),
building_names AS (
  SELECT
    feature->>'id' AS building_id,
    feature#>>'{properties,name,ru}' AS building_name
  FROM buildings
),
joined AS (
  SELECT
    u.unit_id,
    u.room_number,
    lb.building_id,
    bn.building_name,
    row_number() OVER (ORDER BY bn.building_name, u.room_number, u.unit_id) AS rn
  FROM unit_data u
  JOIN level_building lb ON lb.level_id = u.level_id
  JOIN building_names bn ON bn.building_id = lb.building_id
)
INSERT INTO sensors (sensor_id, building_name, room_number, ts, co2, temperature, humidity)
SELECT
  'sensor_' || rn::text AS sensor_id,
  building_name,
  room_number,
  now() AS ts,
  1 AS co2,
  1 AS temperature,
  1 AS humidity
FROM joined;

CREATE TABLE IF NOT EXISTS admins (
  id bigserial PRIMARY KEY,
  login text NOT NULL UNIQUE,
  password text NOT NULL
);

INSERT INTO admins (login, password)
VALUES ('admin', 'admin');


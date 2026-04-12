"""PySpark GPU pipeline — bronze→silver→gold com RAPIDS.

Roda como SparkApplication em cluster mode. O executor pod recebe a
GPU RTX 3090 e o RAPIDS accelera automaticamente as queries SQL.
Resultado final: 5 tabelas gold escritas como parquet no MinIO
(s3a://landing/spark-gold/) para posterior importação no ClickHouse.
"""
import time

from pyspark.sql import SparkSession

OUTPUT_BASE = "s3a://landing/spark-gold"

spark = SparkSession.builder \
    .appName("fhvhv_gpu_pipeline") \
    .getOrCreate()

t0 = time.time()

# ---------------------------------------------------------------------------
# Bronze — ler 12 parquets com CAST pra normalizar INT/BIGINT
# ---------------------------------------------------------------------------
print("=== BRONZE ===")
dfs = []
for m in range(1, 13):
    path = f"s3a://landing/fhvhv-2023/fhvhv_tripdata_2023-{m:02d}.parquet"
    df = spark.read.parquet(path)
    df = df.withColumn("PULocationID", df["PULocationID"].cast("int")) \
           .withColumn("DOLocationID", df["DOLocationID"].cast("int"))
    dfs.append(df)
    print(f"  month {m:02d} loaded")

raw = dfs[0]
for df in dfs[1:]:
    raw = raw.unionByName(df)
raw.createOrReplaceTempView("fhvhv_trips_raw")
raw_count = raw.count()
print(f"  fhvhv_trips_raw: {raw_count:,} rows")

zones = spark.read.option("header", "true").option("inferSchema", "true") \
    .csv("s3a://landing/fhvhv-2023/taxi_zone_lookup.csv")
zones.createOrReplaceTempView("taxi_zones_raw")
print(f"  taxi_zones_raw: {zones.count()} rows")
t_bronze = time.time() - t0
print(f"  bronze: {t_bronze:.1f}s")

# ---------------------------------------------------------------------------
# Silver — clean + enrich
# ---------------------------------------------------------------------------
print("=== SILVER ===")
t1 = time.time()

trips_clean = spark.sql("""
SELECT
    pickup_datetime                                                    AS pickup_at,
    dropoff_datetime                                                   AS dropoff_at,
    CAST(PULocationID AS SMALLINT)                                     AS pickup_location_id,
    CAST(DOLocationID AS SMALLINT)                                     AS dropoff_location_id,
    CAST(trip_miles AS FLOAT)                                          AS trip_miles,
    CAST(base_passenger_fare AS FLOAT)                                 AS base_fare,
    CAST(tips AS FLOAT)                                                AS tips,
    CAST(congestion_surcharge AS FLOAT)                                AS congestion_surcharge,
    CAST(driver_pay AS FLOAT)                                          AS driver_pay,
    shared_request_flag = 'Y'                                          AS shared_requested,
    shared_match_flag = 'Y'                                            AS shared_matched,
    access_a_ride_flag = 'Y'                                           AS access_a_ride,
    wav_request_flag = 'Y'                                             AS wav_requested,
    CAST(TIMESTAMPDIFF(MINUTE, request_datetime, pickup_datetime) AS SMALLINT) AS waiting_minutes,
    CAST(TIMESTAMPDIFF(MINUTE, pickup_datetime, dropoff_datetime) AS SMALLINT) AS trip_minutes,
    CAST(base_passenger_fare + tolls + bcf + sales_tax
         + congestion_surcharge + airport_fee + tips AS FLOAT)         AS total_amount,
    CASE WHEN base_passenger_fare > 0
         THEN CAST(driver_pay / base_passenger_fare * 100 AS FLOAT)
         ELSE 0.0
    END                                                                AS driver_pct_of_fare
FROM fhvhv_trips_raw
WHERE pickup_datetime >= TIMESTAMP '2023-01-01'
  AND pickup_datetime <  TIMESTAMP '2024-01-01'
  AND base_passenger_fare > 0
  AND trip_miles BETWEEN 0 AND 200
  AND trip_time BETWEEN 0 AND 21600
""")
trips_clean.createOrReplaceTempView("trips_clean")
clean_count = trips_clean.count()
print(f"  trips_clean: {clean_count:,} rows")

trips_enriched = spark.sql("""
SELECT
    t.pickup_at, t.dropoff_at, t.waiting_minutes, t.trip_minutes,
    t.trip_miles, t.base_fare, t.tips, t.driver_pay, t.total_amount,
    t.driver_pct_of_fare, t.shared_requested, t.shared_matched,
    t.wav_requested, t.access_a_ride,
    pu.Borough  AS pickup_borough,  pu.Zone  AS pickup_zone,
    do_z.Borough AS dropoff_borough, do_z.Zone AS dropoff_zone
FROM trips_clean t
LEFT JOIN taxi_zones_raw pu    ON pu.LocationID = t.pickup_location_id
LEFT JOIN taxi_zones_raw do_z  ON do_z.LocationID = t.dropoff_location_id
""")
trips_enriched.createOrReplaceTempView("trips_enriched")
t_silver = time.time() - t1
print(f"  silver: {t_silver:.1f}s")

# ---------------------------------------------------------------------------
# Gold — 5 tabelas de agregação → parquet no MinIO
# ---------------------------------------------------------------------------
print("=== GOLD ===")
t2 = time.time()

gold_models = {
    "daily_revenue": """
        SELECT
            CAST(pickup_at AS DATE)                          AS trip_date,
            COUNT(*)                                         AS total_trips,
            ROUND(SUM(total_amount), 2)                      AS gross_revenue_usd,
            ROUND(SUM(driver_pay), 2)                        AS total_driver_pay_usd,
            ROUND(SUM(tips), 2)                              AS total_tips_usd,
            ROUND(SUM(congestion_surcharge), 2)              AS total_congestion_usd,
            ROUND(AVG(trip_miles), 2)                         AS avg_trip_miles,
            ROUND(AVG(trip_minutes), 2)                       AS avg_trip_minutes,
            ROUND(AVG(waiting_minutes), 2)                    AS avg_waiting_minutes,
            ROUND(PERCENTILE_APPROX(total_amount, 0.5), 2)   AS median_fare_usd,
            ROUND(PERCENTILE_APPROX(total_amount, 0.95), 2)  AS p95_fare_usd
        FROM trips_clean
        GROUP BY trip_date
    """,
    "hourly_demand": """
        SELECT
            DAYOFWEEK(pickup_at)          AS weekday,
            HOUR(pickup_at)               AS hour_of_day,
            COUNT(*)                      AS trips,
            ROUND(AVG(trip_minutes), 2)   AS avg_trip_min,
            ROUND(AVG(waiting_minutes), 2) AS avg_wait_min,
            ROUND(AVG(total_amount), 2)   AS avg_fare_usd,
            ROUND(AVG(driver_pay), 2)     AS avg_driver_pay_usd
        FROM trips_clean
        GROUP BY weekday, hour_of_day
    """,
    "borough_pairs": """
        SELECT
            pickup_borough, dropoff_borough,
            COUNT(*)                        AS trips,
            ROUND(SUM(total_amount), 2)     AS revenue_usd,
            ROUND(AVG(trip_miles), 2)       AS avg_miles,
            ROUND(AVG(trip_minutes), 2)     AS avg_minutes,
            ROUND(AVG(total_amount), 2)     AS avg_fare_usd
        FROM trips_enriched
        WHERE pickup_borough IS NOT NULL AND dropoff_borough IS NOT NULL
        GROUP BY pickup_borough, dropoff_borough
    """,
    "driver_economics": """
        SELECT
            DATE_TRUNC('month', pickup_at)                                    AS month,
            COUNT(*)                                                          AS total_trips,
            ROUND(AVG(base_fare), 2)                                          AS avg_base_fare,
            ROUND(AVG(tips), 2)                                               AS avg_tips,
            ROUND(AVG(driver_pay), 2)                                         AS avg_driver_pay,
            ROUND(AVG(driver_pct_of_fare), 2)                                 AS avg_driver_pct_of_fare,
            ROUND(SUM(driver_pay), 2)                                         AS total_driver_pay,
            ROUND(SUM(driver_pay) / NULLIF(SUM(trip_minutes) / 60.0, 0), 2)  AS approx_hourly_rate_usd
        FROM trips_clean
        GROUP BY month
    """,
    "shared_vs_solo": """
        SELECT
            CASE
                WHEN shared_matched THEN 'shared_matched'
                WHEN shared_requested THEN 'shared_unmatched'
                ELSE 'solo'
            END                            AS ride_type,
            COUNT(*)                       AS trips,
            ROUND(AVG(total_amount), 2)    AS avg_total_usd,
            ROUND(AVG(trip_miles), 2)      AS avg_miles,
            ROUND(AVG(trip_minutes), 2)    AS avg_minutes,
            ROUND(AVG(driver_pay), 2)      AS avg_driver_pay_usd,
            ROUND(SUM(total_amount), 2)    AS total_revenue_usd
        FROM trips_clean
        GROUP BY ride_type
    """,
}

for name, query in gold_models.items():
    gt = time.time()
    df = spark.sql(query)
    df.write.mode("overwrite").parquet(f"{OUTPUT_BASE}/{name}/")
    rows = df.count()
    print(f"  {name}: {rows:,} rows ({time.time() - gt:.1f}s)")

t_gold = time.time() - t2
total = time.time() - t0
print(f"  gold: {t_gold:.1f}s")
print(f"=== TOTAL: {total:.1f}s ===")

spark.stop()

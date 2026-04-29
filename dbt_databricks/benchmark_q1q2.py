#!/usr/bin/env python3
"""
Benchmark Q1/Q2 nas 3 camadas do medalhão Databricks.
Espelha a metodologia da DAG benchmark_medallion (ClickHouse): 2 warm-ups + 5 medições.
Saída: JSON com timings por camada/query, salvo em tcc/evidencias/.
"""
import json, os, time, statistics, requests, sys, datetime

HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
WH = os.environ["DATABRICKS_WAREHOUSE_ID"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

QUERIES = {
    "Q1_daily_revenue_2023": {
        "bronze": """
            SELECT
                date(pickup_datetime) AS trip_date,
                count(*) AS trips,
                round(sum(
                    cast(base_passenger_fare AS DOUBLE) + cast(tolls AS DOUBLE)
                    + cast(bcf AS DOUBLE) + cast(sales_tax AS DOUBLE)
                    + cast(congestion_surcharge AS DOUBLE) + cast(airport_fee AS DOUBLE)
                    + cast(tips AS DOUBLE)
                ), 2) AS revenue_usd
            FROM workspace.bronze.fhvhv_trips
            WHERE pickup_datetime >= TIMESTAMP '2023-01-01'
              AND pickup_datetime <  TIMESTAMP '2024-01-01'
              AND base_passenger_fare > 0
            GROUP BY date(pickup_datetime)
            ORDER BY trip_date
        """,
        "silver": """
            SELECT
                date(pickup_at) AS trip_date,
                count(*) AS trips,
                round(sum(total_amount), 2) AS revenue_usd
            FROM workspace.silver.fhvhv_trips_clean
            GROUP BY date(pickup_at)
            ORDER BY trip_date
        """,
        "gold": """
            SELECT trip_date, total_trips AS trips, gross_revenue_usd AS revenue_usd
            FROM workspace.gold.daily_revenue
            ORDER BY trip_date
        """,
    },
    "Q2_top_borough_pairs_by_revenue": {
        "bronze": """
            SELECT
                pu.Borough  AS pickup_borough,
                doz.Borough AS dropoff_borough,
                count(*) AS trips,
                round(sum(
                    cast(base_passenger_fare AS DOUBLE) + cast(tolls AS DOUBLE)
                    + cast(bcf AS DOUBLE) + cast(sales_tax AS DOUBLE)
                    + cast(congestion_surcharge AS DOUBLE) + cast(airport_fee AS DOUBLE)
                    + cast(tips AS DOUBLE)
                ), 2) AS revenue_usd
            FROM workspace.bronze.fhvhv_trips t
            LEFT JOIN workspace.bronze.taxi_zones pu
                   ON cast(pu.LocationID AS SMALLINT) = cast(t.PULocationID AS SMALLINT)
            LEFT JOIN workspace.bronze.taxi_zones doz
                   ON cast(doz.LocationID AS SMALLINT) = cast(t.DOLocationID AS SMALLINT)
            WHERE pickup_datetime >= TIMESTAMP '2023-01-01'
              AND pickup_datetime <  TIMESTAMP '2024-01-01'
              AND base_passenger_fare > 0
              AND pu.Borough IS NOT NULL
              AND doz.Borough IS NOT NULL
            GROUP BY pu.Borough, doz.Borough
            ORDER BY revenue_usd DESC
            LIMIT 10
        """,
        "silver": """
            SELECT
                pickup_borough,
                dropoff_borough,
                count(*) AS trips,
                round(sum(total_amount), 2) AS revenue_usd
            FROM workspace.silver.fhvhv_trips_enriched
            WHERE pickup_borough IS NOT NULL
              AND dropoff_borough IS NOT NULL
            GROUP BY pickup_borough, dropoff_borough
            ORDER BY revenue_usd DESC
            LIMIT 10
        """,
        "gold": """
            SELECT pickup_borough, dropoff_borough, trips, revenue_usd
            FROM workspace.gold.borough_pairs
            WHERE pickup_borough IS NOT NULL
              AND dropoff_borough IS NOT NULL
            ORDER BY revenue_usd DESC
            LIMIT 10
        """,
    },
}

WARMUPS = 2
MEASUREMENTS = 5


def run_sql(sql: str) -> dict:
    """Submit statement, wait, return server-timing + row count."""
    t_client_start = time.time()
    r = requests.post(
        f"https://{HOST}/api/2.0/sql/statements",
        headers=H,
        json={"warehouse_id": WH, "statement": sql, "wait_timeout": "50s"},
        timeout=120,
    )
    d = r.json()
    sid = d.get("statement_id")
    state = d.get("status", {}).get("state")
    while state in ("PENDING", "RUNNING"):
        time.sleep(0.5)
        r = requests.get(
            f"https://{HOST}/api/2.0/sql/statements/{sid}", headers=H, timeout=60
        )
        d = r.json()
        state = d.get("status", {}).get("state")
    t_client_end = time.time()
    if state != "SUCCEEDED":
        raise RuntimeError(f"query failed: {d.get('status',{}).get('error',{})}")
    # try to extract server-side timing from response (manifest.metrics not always populated)
    res = d.get("result", {})
    rows_returned = res.get("row_count", 0) or len(res.get("data_array") or [])
    return {
        "statement_id": sid,
        "client_wall_ms": (t_client_end - t_client_start) * 1000,
        "rows_returned": rows_returned,
    }


def benchmark_cell(query_label, layer, sql):
    print(f"  {query_label} / {layer}: warming up x{WARMUPS}...")
    for _ in range(WARMUPS):
        run_sql(sql)
    print(f"    measuring x{MEASUREMENTS}:")
    samples = []
    for i in range(MEASUREMENTS):
        m = run_sql(sql)
        samples.append(m)
        print(f"      run {i+1}: {m['client_wall_ms']:.1f} ms (rows={m['rows_returned']})")
    durations = [s["client_wall_ms"] for s in samples]
    return {
        "samples": samples,
        "mean_ms": statistics.mean(durations),
        "median_ms": statistics.median(durations),
        "stdev_ms": statistics.stdev(durations) if len(durations) > 1 else 0,
        "cv_pct": (statistics.stdev(durations) / statistics.mean(durations) * 100) if len(durations) > 1 else 0,
    }


def main():
    started = datetime.datetime.utcnow().isoformat() + "Z"
    print(f"=== benchmark started {started} ===")
    print(f"warehouse: {WH}  warmups={WARMUPS}  measurements={MEASUREMENTS}")
    print()

    results = {}
    for query_label, layers in QUERIES.items():
        print(f"--- {query_label} ---")
        results[query_label] = {}
        for layer, sql in layers.items():
            results[query_label][layer] = benchmark_cell(query_label, layer, sql)
        print()

    # speedup gold/bronze
    for q in results:
        bronze_mean = results[q]["bronze"]["mean_ms"]
        gold_mean = results[q]["gold"]["mean_ms"]
        silver_mean = results[q]["silver"]["mean_ms"]
        results[q]["speedup_gold_over_bronze"] = bronze_mean / gold_mean if gold_mean else None
        results[q]["speedup_silver_over_bronze"] = bronze_mean / silver_mean if silver_mean else None

    finished = datetime.datetime.utcnow().isoformat() + "Z"
    payload = {
        "engine": "Databricks Serverless SQL Warehouse 2X-Small",
        "warehouse_id": WH,
        "host": HOST,
        "dataset": "fhvhv_tripdata_2023-01.parquet (18,479,031 rows)",
        "warmups": WARMUPS,
        "measurements": MEASUREMENTS,
        "started_utc": started,
        "finished_utc": finished,
        "queries": results,
    }

    out = "/home/ubuntu/mba_usp-data_stack/tcc/evidencias/databricks_benchmark.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"=== saved to {out} ===")

    print("\n=== summary ===")
    for q, layers in results.items():
        print(f"\n{q}:")
        print(f"  {'layer':<8} {'mean_ms':>10} {'median_ms':>10} {'cv%':>6}")
        for layer in ("bronze", "silver", "gold"):
            r = layers[layer]
            print(f"  {layer:<8} {r['mean_ms']:>10.1f} {r['median_ms']:>10.1f} {r['cv_pct']:>5.1f}")
        print(
            f"  speedup gold/bronze:   {layers['speedup_gold_over_bronze']:.1f}x  |  "
            f"silver/bronze: {layers['speedup_silver_over_bronze']:.1f}x"
        )


if __name__ == "__main__":
    main()

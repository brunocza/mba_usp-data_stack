"""Benchmark da arquitetura Medallion — bronze vs silver vs gold.

Este DAG materializa a evidencia central do TCC: a arquitetura medallion
(bronze raw -> silver clean -> gold pre-aggregated) gera ganho mensuravel
de performance em queries analiticas.

A mesma pergunta de negocio e executada em cada uma das 3 camadas, e
medimos via `system.query_log` do ClickHouse:
    - query_duration_ms    (latencia reportada pelo engine)
    - read_rows            (linhas escaneadas do disco)
    - read_bytes           (bytes lidos do disco)
    - memory_usage         (pico de memoria da query)
    - result_rows          (linhas no resultado final)

Alem disso, medimos o wall-clock no lado Python (inclui round-trip HTTP).

COLETA DE METRICAS (approach validado em 2026-04-12):
    1. Cada query e tagueada com um `log_comment` unico passado via settings.
    2. O ClickHouse registra automaticamente essa query em system.query_log.
    3. Apos rodar todas as iteracoes de uma camada, executamos
       SYSTEM FLUSH LOGS e consultamos system.query_log filtrando por
       log_comment. Isso da os numeros definitivos do engine, que sao MUITO
       mais confiaveis que qualquer proxy cliente.

UNIDADE DE TESTE:
    1 run desta DAG = 1 TESTE = 1 ponto no historico.
    Pra gerar N amostras, trigger a DAG N vezes (manual ou agendado).
    Cada run tem seu proprio run_id + captured_at, e todos os runs ficam
    empilhados em benchmark.medallion_results.
    A consistencia estatistica e aferida CROSS-RUN pelo task report_history,
    que compara N execucoes e calcula stddev + coeficiente de variacao (CV).

As queries sao escolhidas para serem semanticamente equivalentes, mas com
complexidade decrescente:
    Q1 — "Receita diaria do ano de 2023"
    Q2 — "Top 10 pares origem-destino por borough, por receita"

Pre-requisito: o DAG `fhvhv_pipeline` deve ter rodado pelo menos uma vez,
populando bronze.fhvhv_trips, silver.fhvhv_trips_clean,
silver.fhvhv_trips_enriched, gold.daily_revenue e gold.borough_pairs.

Output:
    - Tabela `benchmark.medallion_results` no ClickHouse com os dados brutos
    - Relatorio formatado nos logs do Airflow (stdout) pra screenshot
"""
from __future__ import annotations

import time
from datetime import datetime

from airflow.models.dag import DAG
from airflow.providers.standard.operators.python import PythonOperator

# -----------------------------------------------------------------------------
# Config — overridavel via DAG params na UI do Airflow
# -----------------------------------------------------------------------------
# IMPORTANTE — unidade de "teste":
#   1 run desta DAG = 1 teste = 1 ponto no historico da benchmark.medallion_results.
#   Pra gerar N amostras de um teste consistente, voce deve trigger a DAG N vezes
#   (manualmente na UI ou agendando via schedule='0 */1 * * *', por exemplo).
#
#   As iteracoes DENTRO de um run servem apenas pra reduzir o ruido de uma
#   unica medicao (evitar outlier por scheduler jitter). Nao sao amostras
#   independentes pra fins estatisticos. A consistencia do benchmark e aferida
#   CROSS-RUN pelo task `report_history`, que compara N execucoes da DAG.
DEFAULT_WARMUP_RUNS = 2     # descartadas (cache warmup)
DEFAULT_MEASURED_RUNS = 5   # reduz ruido dentro de 1 teste

# Pares (label, sql) por camada. As queries sao SEMANTICAMENTE equivalentes:
# todas respondem a mesma pergunta de negocio, mas com graus muito diferentes
# de complexidade computacional.
QUERIES: dict[str, dict[str, str]] = {
    "Q1_daily_revenue_2023": {
        "bronze": """
            SELECT
                toDate(pickup_datetime) AS trip_date,
                count() AS trips,
                round(sum(
                    toFloat64(base_passenger_fare) + toFloat64(tolls)
                    + toFloat64(bcf) + toFloat64(sales_tax)
                    + toFloat64(congestion_surcharge) + toFloat64(airport_fee)
                    + toFloat64(tips)
                ), 2) AS revenue_usd
            FROM bronze.fhvhv_trips
            WHERE pickup_datetime >= toDateTime('2023-01-01')
              AND pickup_datetime <  toDateTime('2024-01-01')
              AND base_passenger_fare > 0
            GROUP BY trip_date
            ORDER BY trip_date
        """,
        "silver": """
            SELECT
                toDate(pickup_at) AS trip_date,
                count() AS trips,
                round(sum(total_amount), 2) AS revenue_usd
            FROM silver.fhvhv_trips_clean
            GROUP BY trip_date
            ORDER BY trip_date
        """,
        "gold": """
            SELECT trip_date, total_trips AS trips, gross_revenue_usd AS revenue_usd
            FROM gold.daily_revenue
            ORDER BY trip_date
        """,
    },
    "Q2_top_borough_pairs_by_revenue": {
        "bronze": """
            SELECT
                pu.Borough  AS pickup_borough,
                doz.Borough AS dropoff_borough,
                count() AS trips,
                round(sum(
                    toFloat64(base_passenger_fare) + toFloat64(tolls)
                    + toFloat64(bcf) + toFloat64(sales_tax)
                    + toFloat64(congestion_surcharge) + toFloat64(airport_fee)
                    + toFloat64(tips)
                ), 2) AS revenue_usd
            FROM bronze.fhvhv_trips t
            LEFT JOIN bronze.taxi_zones pu
                   ON pu.LocationID = toUInt16OrNull(toString(t.PULocationID))
            LEFT JOIN bronze.taxi_zones doz
                   ON doz.LocationID = toUInt16OrNull(toString(t.DOLocationID))
            WHERE pickup_datetime >= toDateTime('2023-01-01')
              AND pickup_datetime <  toDateTime('2024-01-01')
              AND base_passenger_fare > 0
              AND pu.Borough IS NOT NULL
              AND doz.Borough IS NOT NULL
            GROUP BY pickup_borough, dropoff_borough
            ORDER BY revenue_usd DESC
            LIMIT 10
        """,
        "silver": """
            SELECT
                pickup_borough,
                dropoff_borough,
                count() AS trips,
                round(sum(total_amount), 2) AS revenue_usd
            FROM silver.fhvhv_trips_enriched
            WHERE pickup_borough IS NOT NULL
              AND dropoff_borough IS NOT NULL
            GROUP BY pickup_borough, dropoff_borough
            ORDER BY revenue_usd DESC
            LIMIT 10
        """,
        "gold": """
            SELECT pickup_borough, dropoff_borough, trips, revenue_usd
            FROM gold.borough_pairs
            WHERE pickup_borough IS NOT NULL
              AND dropoff_borough IS NOT NULL
            ORDER BY revenue_usd DESC
            LIMIT 10
        """,
    },
}

LAYERS = ("bronze", "silver", "gold")


# -----------------------------------------------------------------------------
# ClickHouse helpers
# -----------------------------------------------------------------------------
def _client():
    import os

    import clickhouse_connect

    return clickhouse_connect.get_client(
        host=os.environ["CLICKHOUSE_HOST"],
        port=int(os.environ["CLICKHOUSE_PORT"]),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )


def _human_bytes(n: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:,.2f} {u}"
        f /= 1024
    return f"{n} B"


# -----------------------------------------------------------------------------
# Tasks
# -----------------------------------------------------------------------------
def setup_benchmark_schema(**_):
    """Cria schema e tabela onde os resultados serao persistidos."""
    c = _client()
    c.command("CREATE DATABASE IF NOT EXISTS benchmark")
    c.command(
        """
        CREATE TABLE IF NOT EXISTS benchmark.medallion_results (
            run_id              String,
            captured_at         DateTime DEFAULT now(),
            question_id         String,
            layer               LowCardinality(String),
            iteration           UInt8,
            wall_ms             Float64,
            query_duration_ms   UInt32,
            read_rows           UInt64,
            read_bytes          UInt64,
            memory_usage        UInt64,
            result_rows         UInt64
        )
        ENGINE = MergeTree()
        ORDER BY (captured_at, question_id, layer, iteration)
        """
    )
    print("  ok: benchmark.medallion_results pronto")


def collect_table_stats(**ctx):
    """Coleta row count, tamanho em disco e razao de compressao por tabela."""
    c = _client()
    rows = c.query(
        """
        SELECT
            database,
            table,
            sum(rows)                       AS rows,
            sum(bytes_on_disk)              AS bytes_on_disk,
            sum(data_uncompressed_bytes)    AS bytes_uncompressed
        FROM system.parts
        WHERE active
          AND database IN ('bronze','silver','gold')
          AND table IN (
              'fhvhv_trips','taxi_zones',
              'fhvhv_trips_clean',
              'daily_revenue','hourly_demand','borough_pairs',
              'driver_economics','shared_vs_solo'
          )
        GROUP BY database, table
        ORDER BY database, table
        """
    ).result_rows

    if not rows:
        raise RuntimeError(
            "Nenhuma tabela encontrada em bronze/silver/gold. "
            "Rode o DAG fhvhv_pipeline antes deste benchmark."
        )

    print()
    print("=" * 90)
    print("ESTATISTICAS DAS TABELAS (system.parts)")
    print("=" * 90)
    print(f"{'database':<10} {'table':<22} {'rows':>15} {'on_disk':>14} {'raw':>14} {'ratio':>8}")
    print("-" * 90)
    for db, tbl, n_rows, on_disk, raw in rows:
        ratio = (raw / on_disk) if on_disk else 0
        print(
            f"{db:<10} {tbl:<22} {n_rows:>15,} "
            f"{_human_bytes(on_disk):>14} {_human_bytes(raw):>14} "
            f"{ratio:>7.2f}x"
        )
    print()

    # Empilhar pra usar na consolidacao
    ctx["ti"].xcom_push(
        key="table_stats",
        value=[
            {
                "database": db,
                "table": tbl,
                "rows": int(r),
                "bytes_on_disk": int(d),
                "bytes_uncompressed": int(u),
                "compression_ratio": (u / d) if d else 0.0,
            }
            for db, tbl, r, d, u in rows
        ],
    )


def _tag(run_id: str, q_id: str, layer: str, iteration: int) -> str:
    """Gera log_comment unico pra amarrar cada execucao ao system.query_log."""
    return f"tcc_bench|{run_id}|{q_id}|{layer}|i{iteration}"


def _benchmark_layer(
    layer: str,
    run_id: str,
    warmup_runs: int = DEFAULT_WARMUP_RUNS,
    measured_runs: int = DEFAULT_MEASURED_RUNS,
) -> list[dict]:
    """Roda todas as queries da camada `layer` (warmup + medicoes).

    Estrategia:
        1. Roda a query com um log_comment unico por iteracao.
        2. Mede o wall-clock no Python (round-trip HTTP incluso).
        3. Apos terminar TODAS as iteracoes, faz SYSTEM FLUSH LOGS uma vez
           e consulta system.query_log pra enriquecer cada iteracao com
           query_duration_ms, read_rows, read_bytes, memory_usage.
    """
    c = _client()
    results: list[dict] = []

    print()
    print("=" * 90)
    print(
        f"BENCHMARK CAMADA: {layer.upper()}  "
        f"(warmup={warmup_runs}, measured={measured_runs})"
    )
    print("=" * 90)

    for q_id, by_layer in QUERIES.items():
        sql = by_layer[layer].strip()

        # Warmup — descartado. Serve pra aquecer caches e amortizar
        # efeitos de JIT / compilacao do ClickHouse.
        for _ in range(warmup_runs):
            c.query(sql)

        # Medicoes — cada iteracao recebe um log_comment unico.
        per_iter: list[dict] = []
        for i in range(1, measured_runs + 1):
            tag = _tag(run_id, q_id, layer, i)
            t0 = time.perf_counter()
            res = c.query(sql, settings={"log_comment": tag})
            wall_ms = (time.perf_counter() - t0) * 1000

            per_iter.append(
                {
                    "tag": tag,
                    "wall_ms": wall_ms,
                    "result_rows": len(res.result_rows),
                }
            )

        # Enriquecer com metricas do engine via system.query_log.
        c.command("SYSTEM FLUSH LOGS")
        tags = [x["tag"] for x in per_iter]
        # tuple pra construir a lista pro IN
        in_clause = ",".join(f"'{t}'" for t in tags)
        rows = c.query(
            f"""
            SELECT
                log_comment,
                query_duration_ms,
                read_rows,
                read_bytes,
                memory_usage,
                result_rows
            FROM system.query_log
            WHERE log_comment IN ({in_clause})
              AND type = 'QueryFinish'
            ORDER BY event_time
            """
        ).result_rows

        engine_by_tag = {
            r[0]: {
                "query_duration_ms": int(r[1]),
                "read_rows": int(r[2]),
                "read_bytes": int(r[3]),
                "memory_usage": int(r[4]),
                "result_rows": int(r[5]),
            }
            for r in rows
        }

        # Consolidar: wall (cliente) + engine (ClickHouse).
        for idx, it in enumerate(per_iter, start=1):
            eng = engine_by_tag.get(it["tag"], {})
            results.append(
                {
                    "run_id": run_id,
                    "question_id": q_id,
                    "layer": layer,
                    "iteration": idx,
                    "wall_ms": it["wall_ms"],
                    "query_duration_ms": eng.get("query_duration_ms", 0),
                    "read_rows": eng.get("read_rows", 0),
                    "read_bytes": eng.get("read_bytes", 0),
                    "memory_usage": eng.get("memory_usage", 0),
                    "result_rows": eng.get("result_rows", it["result_rows"]),
                }
            )

        # Sumario por query
        q_items = [r for r in results if r["question_id"] == q_id]
        avg_wall = sum(x["wall_ms"] for x in q_items) / len(q_items)
        avg_engine = sum(x["query_duration_ms"] for x in q_items) / len(q_items)
        avg_bytes = sum(x["read_bytes"] for x in q_items) / len(q_items)
        avg_rows = sum(x["read_rows"] for x in q_items) / len(q_items)
        mem_peak = max(x["memory_usage"] for x in q_items)

        print(
            f"  {q_id:<35} "
            f"wall={avg_wall:>8,.1f} ms  "
            f"engine={avg_engine:>8,.1f} ms  "
            f"read={_human_bytes(int(avg_bytes)):>12}  "
            f"scan_rows={int(avg_rows):>14,}  "
            f"mem={_human_bytes(mem_peak):>12}  "
            f"out={q_items[-1]['result_rows']:>5}"
        )

    return results


def _params(ctx) -> tuple[int, int]:
    """Extrai (warmup_runs, measured_runs) dos params do DAG, com defaults."""
    p = ctx.get("params") or {}
    return (
        int(p.get("warmup_runs", DEFAULT_WARMUP_RUNS)),
        int(p.get("measured_runs", DEFAULT_MEASURED_RUNS)),
    )


def benchmark_bronze(**ctx):
    warmup, measured = _params(ctx)
    results = _benchmark_layer("bronze", ctx["run_id"], warmup, measured)
    ctx["ti"].xcom_push(key="bronze_results", value=results)


def benchmark_silver(**ctx):
    warmup, measured = _params(ctx)
    results = _benchmark_layer("silver", ctx["run_id"], warmup, measured)
    ctx["ti"].xcom_push(key="silver_results", value=results)


def benchmark_gold(**ctx):
    warmup, measured = _params(ctx)
    results = _benchmark_layer("gold", ctx["run_id"], warmup, measured)
    ctx["ti"].xcom_push(key="gold_results", value=results)


def consolidate_results(**ctx):
    """Persiste em ClickHouse e gera o relatorio formatado pro TCC."""
    ti = ctx["ti"]
    rows = (
        (ti.xcom_pull(task_ids="benchmark_bronze", key="bronze_results") or [])
        + (ti.xcom_pull(task_ids="benchmark_silver", key="silver_results") or [])
        + (ti.xcom_pull(task_ids="benchmark_gold", key="gold_results") or [])
    )

    if not rows:
        raise RuntimeError("Sem resultados — alguma task de benchmark falhou.")

    # Persistir no ClickHouse
    c = _client()
    c.insert(
        "benchmark.medallion_results",
        data=[
            [
                r["run_id"],
                r["question_id"],
                r["layer"],
                r["iteration"],
                r["wall_ms"],
                r["query_duration_ms"],
                r["read_rows"],
                r["read_bytes"],
                r["memory_usage"],
                r["result_rows"],
            ]
            for r in rows
        ],
        column_names=[
            "run_id",
            "question_id",
            "layer",
            "iteration",
            "wall_ms",
            "query_duration_ms",
            "read_rows",
            "read_bytes",
            "memory_usage",
            "result_rows",
        ],
    )
    print(f"\n  ok: {len(rows)} linhas persistidas em benchmark.medallion_results")

    # Agregar por (question_id, layer)
    from statistics import mean

    agg: dict[tuple[str, str], list] = {}
    for r in rows:
        k = (r["question_id"], r["layer"])
        agg.setdefault(k, []).append(r)

    summary: dict[tuple[str, str], dict] = {}
    for (q, layer), items in agg.items():
        summary[(q, layer)] = {
            "wall_avg": mean(x["wall_ms"] for x in items),
            "wall_min": min(x["wall_ms"] for x in items),
            "wall_max": max(x["wall_ms"] for x in items),
            "engine_avg": mean(x["query_duration_ms"] for x in items),
            "read_bytes": int(mean(x["read_bytes"] for x in items)),
            "read_rows": int(mean(x["read_rows"] for x in items)),
            "memory_peak": max(x["memory_usage"] for x in items),
            "result_rows": items[-1]["result_rows"],
        }

    # Relatorio final
    print()
    print("=" * 110)
    print("RELATORIO FINAL — VALOR DA ARQUITETURA MEDALLION")
    print("=" * 110)
    for q_id in QUERIES.keys():
        print()
        print(f"# {q_id}")
        print(
            f"  {'layer':<8} "
            f"{'wall avg':>10} {'engine avg':>12} "
            f"{'read':>14} {'scan rows':>16} {'mem peak':>12} "
            f"{'speedup':>10}"
        )
        print("  " + "-" * 102)

        bronze_ref = summary.get((q_id, "bronze"), {}).get("engine_avg") or summary.get((q_id, "bronze"), {}).get("wall_avg") or 1
        for layer in LAYERS:
            s = summary.get((q_id, layer))
            if not s:
                continue
            # Speedup baseado no engine (mais justo que wall, que tem ruido de rede)
            ref_val = s["engine_avg"] if s["engine_avg"] else s["wall_avg"]
            speedup = (bronze_ref / ref_val) if ref_val else 0
            print(
                f"  {layer:<8} "
                f"{s['wall_avg']:>9,.1f}ms "
                f"{s['engine_avg']:>11,.1f}ms "
                f"{_human_bytes(s['read_bytes']):>14} "
                f"{s['read_rows']:>16,} "
                f"{_human_bytes(s['memory_peak']):>12} "
                f"{speedup:>9,.1f}x"
            )
    print()
    print("=" * 110)
    print("Resultados persistidos: SELECT * FROM benchmark.medallion_results")
    print("=" * 110)


def report_history(**_):
    """Analise de consistencia sobre TODA a historia da benchmark.medallion_results.

    Gera 3 visoes no log (pra screenshot):
        A. Ultimos 10 runs lado a lado por (pergunta, camada) — mean do engine_ms
        B. Estatisticas per-run: iteracoes, mean, stddev, CV (dentro de cada run)
        C. Estatisticas agregadas cross-run: total de amostras, mean, stddev, CV
           (mostra a consistencia das medicoes atraves do tempo)

    Coeficiente de variacao (CV) < 10% = medicoes consistentes.
    CV entre 10-20% = aceitavel. CV > 20% = investigar fontes de ruido.
    """
    c = _client()

    # ------------------------------------------------------------------
    # A. Ultimos 10 runs — matriz run x (pergunta, camada)
    # ------------------------------------------------------------------
    print()
    print("=" * 110)
    print("A. HISTORICO — ULTIMOS 10 RUNS (engine_ms mean por iteracao)")
    print("=" * 110)

    rows = c.query(
        """
        SELECT
            run_id,
            any(captured_at)                       AS ts,
            question_id,
            layer,
            count()                                AS iters,
            round(avg(query_duration_ms), 1)       AS engine_avg,
            round(stddevPop(query_duration_ms), 1) AS engine_stddev
        FROM benchmark.medallion_results
        GROUP BY run_id, question_id, layer
        ORDER BY ts DESC, question_id, layer
        """
    ).result_rows

    if not rows:
        print("  (sem dados historicos ainda)")
        return

    # Agrupa por run pra imprimir 1 run por "bloco"
    by_run: dict[str, list[tuple]] = {}
    run_meta: dict[str, any] = {}
    for r in rows:
        run_id, ts, q, layer, iters, eng_avg, eng_std = r
        by_run.setdefault(run_id, []).append((q, layer, iters, eng_avg, eng_std))
        run_meta[run_id] = ts

    # Ordena runs pela timestamp desc
    ordered_runs = sorted(by_run.keys(), key=lambda rid: run_meta[rid], reverse=True)[:10]

    for run_id in ordered_runs:
        print()
        print(f"# run_id = {run_id}")
        print(f"  captured_at = {run_meta[run_id]}")
        print(
            f"  {'question':<35} {'layer':<8} {'iters':>6} "
            f"{'engine_avg (ms)':>17} {'stddev':>10} {'CV %':>8}"
        )
        print("  " + "-" * 98)
        for q, layer, iters, eng_avg, eng_std in sorted(by_run[run_id]):
            cv = (eng_std / eng_avg * 100) if eng_avg else 0
            print(
                f"  {q:<35} {layer:<8} {iters:>6} "
                f"{eng_avg:>17,.1f} {eng_std:>10,.1f} {cv:>7.1f}%"
            )

    # ------------------------------------------------------------------
    # B. Consistencia cross-run — mean/stddev agregando TODAS as amostras
    # ------------------------------------------------------------------
    print()
    print("=" * 110)
    print("B. CONSISTENCIA CROSS-RUN — todas as amostras agregadas por (pergunta, camada)")
    print("=" * 110)

    agg = c.query(
        """
        SELECT
            question_id,
            layer,
            count()                                         AS total_samples,
            count(DISTINCT run_id)                          AS total_runs,
            round(avg(query_duration_ms), 1)                AS engine_avg,
            round(quantile(0.5)(query_duration_ms), 1)      AS engine_p50,
            round(quantile(0.95)(query_duration_ms), 1)     AS engine_p95,
            round(stddevPop(query_duration_ms), 1)          AS engine_stddev,
            round(avg(wall_ms), 1)                          AS wall_avg,
            round(stddevPop(wall_ms), 1)                    AS wall_stddev,
            any(read_rows)                                  AS read_rows,
            formatReadableSize(any(read_bytes))             AS read_bytes_h
        FROM benchmark.medallion_results
        GROUP BY question_id, layer
        ORDER BY question_id, multiIf(layer='bronze',1,layer='silver',2,3)
        """
    ).result_rows

    print(
        f"  {'question':<32} {'layer':<8} {'samples':>8} {'runs':>5} "
        f"{'engine_avg':>11} {'p50':>8} {'p95':>8} {'stddev':>9} "
        f"{'CV %':>7} {'read_rows':>14} {'read_bytes':>12}"
    )
    print("  " + "-" * 128)
    for r in agg:
        q, layer, n, runs, eavg, ep50, ep95, estd, wavg, wstd, rrows, rbytes = r
        cv = (estd / eavg * 100) if eavg else 0
        print(
            f"  {q:<32} {layer:<8} {n:>8} {runs:>5} "
            f"{eavg:>10,.1f}ms {ep50:>7,.1f} {ep95:>7,.1f} "
            f"{estd:>9,.1f} {cv:>6.1f}% "
            f"{int(rrows):>14,} {rbytes:>12}"
        )

    # ------------------------------------------------------------------
    # C. Interpretacao automatica do CV
    # ------------------------------------------------------------------
    print()
    print("=" * 110)
    print("C. INTERPRETACAO DA CONSISTENCIA (CV = coeficiente de variacao)")
    print("=" * 110)
    print("  CV < 10%  : excelente — medicoes consistentes e confiaveis")
    print("  CV 10-20% : aceitavel — ruido moderado")
    print("  CV > 20%  : investigar — alta variabilidade entre execucoes")
    print()
    good = sum(1 for r in agg if r[6] and r[7] and (r[7] / r[4] * 100) < 10)
    total = len(agg)
    print(f"  Medicoes com CV<10%: {good}/{total}")
    print()
    print("Query pra explorar o historico completo:")
    print("  SELECT * FROM benchmark.medallion_results ORDER BY captured_at DESC LIMIT 100;")
    print("=" * 110)


# -----------------------------------------------------------------------------
# DAG
# -----------------------------------------------------------------------------
with DAG(
    dag_id="benchmark_medallion",
    description="TCC: prova quantitativa do valor da arquitetura medallion (bronze vs silver vs gold)",
    start_date=datetime(2026, 4, 12),
    schedule=None,
    catchup=False,
    max_active_tasks=4,
    tags=["tcc", "benchmark", "medallion", "clickhouse"],
    params={
        "warmup_runs": DEFAULT_WARMUP_RUNS,
        "measured_runs": DEFAULT_MEASURED_RUNS,
    },
) as dag:

    t_setup = PythonOperator(
        task_id="setup_benchmark_schema",
        python_callable=setup_benchmark_schema,
    )

    t_stats = PythonOperator(
        task_id="collect_table_stats",
        python_callable=collect_table_stats,
    )

    t_bronze = PythonOperator(
        task_id="benchmark_bronze",
        python_callable=benchmark_bronze,
    )

    t_silver = PythonOperator(
        task_id="benchmark_silver",
        python_callable=benchmark_silver,
    )

    t_gold = PythonOperator(
        task_id="benchmark_gold",
        python_callable=benchmark_gold,
    )

    t_report = PythonOperator(
        task_id="consolidate_results",
        python_callable=consolidate_results,
    )

    t_history = PythonOperator(
        task_id="report_history",
        python_callable=report_history,
    )

    t_setup >> t_stats >> [t_bronze, t_silver, t_gold] >> t_report >> t_history

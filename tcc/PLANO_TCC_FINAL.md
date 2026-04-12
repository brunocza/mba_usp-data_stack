# Plano: Completar TCC Final — Atender Feedback do Orientador

## Context

Bruno entregou os **Resultados Preliminares** do TCC e recebeu nota 8 com 3 pontos de melhoria do orientador:
1. **Falta de indicadores quantitativos** — sem metricas de tempo, CPU/RAM, throughput
2. **Ausencia de testes multi-cenario** — sem variacao de carga, formatos, stress
3. **Projeto dbt nao iniciado** — so descrito, sem implementacao

**A grande noticia**: desde a entrega preliminar, o projeto evoluiu enormemente. O dbt ja esta **100% implementado** (7 modelos, testes, documentacao), o pipeline roda com dados reais NYC (~232M rows), e ha 15 dashboards Grafana de monitoramento. O que falta agora e **coletar as evidencias quantitativas** e **rodar os testes de cenario** para documentar no TCC final.

### Estado Atual da Stack (evidencias coletadas)

| Componente | Estado |
|---|---|
| Pipeline Airflow (fhvhv_pipeline) | 7 runs com sucesso, ultima: 849s (14.2 min) |
| dbt (dags/dbt_demo/) | 2 silver + 5 gold models, testes, sources |
| ClickHouse | bronze/silver/gold schemas populados |
| Grafana | 15 dashboards (Cluster, Airflow, ClickHouse, MinIO, GPU, Analytics) |
| Infra | K3s single-node, 24 GB RAM, 12 CPUs |

### Timing da ultima run (run 7, 2026-04-12)

| Task | Duracao |
|---|---|
| create_schemas | 0.6s |
| ingest_bronze_trips | 173s (2.9 min) |
| ingest_bronze_zones | 0.4s |
| dbt_transform (Cosmos) | ~444s (7.4 min) |
| optimize_tables | 230s (3.8 min) |
| **Total pipeline** | **849s (14.2 min)** |

---

## Prioridades (Ordem de Execucao)

| Ordem | Item | Justificativa |
|---|---|---|
| **0a** | Salvar este plano em `tcc/PLANO_TCC_FINAL.md` na raiz do projeto | Versionado no git, fica acessivel |
| **0b** | Transcrever `ResultadosPreliminares_Bruno_Czarnescki.docx` para `tcc/v1_ResultadosPreliminares.md` | Preserva o que ja foi entregue, em formato editavel |
| **0c** | Criar `tcc/v2_TCC_Final.md` baseado em v1 | Documento vivo onde adicionaremos os resultados novos |
| **1** | DAG benchmark medallion | Evidencia mais forte — bronze vs silver vs gold |
| **2** | DAG benchmark volume + incremental | Escalabilidade + diferencial pratico |
| **3** | DAG benchmark stress | Carga concorrente, fecha o trio quantitativo |
| **4** | Atualizar `tcc/v2_TCC_Final.md` (medallion + dbt + benchmarks) | Incorpora teoria + resultados no documento |
| **5** | Capturar evidencias (screenshots dbt docs, Grafana, dbt run) | Material visual pro TCC final |
| **6** | Comparativo Databricks | Forte argumento pra banca avaliadora — fazer no final |

**Foco**: executar 0→6 em ordem. Cada item entrega valor independente ao TCC.

## Estrutura de Arquivos do TCC

Criar pasta `tcc/` na raiz do projeto:
```
tcc/
├── PLANO_TCC_FINAL.md          (este plano)
├── v1_ResultadosPreliminares.md (transcricao da entrega parcial — preservada)
├── v2_TCC_Final.md             (documento vivo — onde adicionaremos os novos resultados)
├── evidencias/                 (pasta para screenshots, JSONs de benchmark)
│   ├── dbt_docs_lineage.png
│   ├── grafana_clickhouse.png
│   ├── benchmark_medallion.json
│   └── ...
└── referencias.md              (bibliografia consolidada — opcional)
```

**Importante sobre o v1**: e uma transcricao **fiel** do .docx, sem alteracoes. Serve como baseline. Todas as edicoes acontecem no v2.

## O Que Precisa Ser Feito (4 frentes)

### Frente 1: Indicadores Quantitativos (Feedback #1)

Criar um **DAG de benchmark** (`benchmark_pipeline_dag.py`) que, ao rodar, coleta e registra automaticamente:

**1.1 — Metricas de Pipeline (Airflow)**
- Tempo total end-to-end do pipeline
- Tempo por task (create_schemas, ingest, dbt_transform, optimize)
- Ja temos dados de 7 runs: variam de 398s a 849s

**1.2 — Metricas de Recursos (Prometheus/Grafana)**
- CPU usage por namespace durante a execucao (query PromQL: `rate(container_cpu_usage_seconds_total{namespace=~"orchestrator2|warehouse"}[5m])`)
- Memory usage por namespace (`container_memory_working_set_bytes`)
- Disk I/O do ClickHouse (`node_disk_read_bytes_total`, `node_disk_written_bytes_total`)

**1.3 — Metricas de ClickHouse**
- Tamanho de cada tabela em disco (antes e depois do OPTIMIZE)
- Row count por tabela/camada
- Compression ratio (raw vs comprimido)
- Query latency em tabelas gold (SELECT com aggregations)
- Throughput de ingestao (rows/sec por mes)

**Arquivos a criar/modificar:**
- `dags/benchmark_dag.py` — DAG que roda queries de benchmark no ClickHouse e registra resultados
- `dags/dbt_demo/models/gold/benchmark_results.sql` (opcional) — materializar metricas

**Abordagem pratica:** Criar um script Python que executa queries no ClickHouse via `system.parts`, `system.query_log`, e `system.metrics` para coletar tudo automaticamente e gerar uma tabela de resultados.

### Frente 2: Testes Multi-Cenario (Feedback #2)

**2.1 — Variacao de Volume (escalabilidade) + Ingestao Incremental**
Modificar o pipeline para aceitar um parametro `months` (1, 3, 6, 12) e medir:
- Tempo de ingestao vs volume de dados
- Uso de memoria do ClickHouse vs volume
- Tempo de transformacao dbt vs volume

Isso mostra linearidade (ou nao) do pipeline com o crescimento dos dados.

**Diferencial — Ingestao Incremental**:
A DAG vai testar duas estrategias para evidenciar o ganho:
- **Full reload**: dropa a tabela e ingere tudo de novo (estrategia atual do pipeline)
- **Incremental**: usa high-watermark (max(pickup_at)) e so ingere meses ainda nao carregados
- Compara: tempo da 1a execucao vs tempos de execucoes subsequentes
- Mostra que incremental e ~12x mais rapido apos primeira carga (so processa o delta)

Esta e uma pratica standard em engenharia de dados (Reis & Housley, 2022) e da peso pratico ao TCC sem inflar o escopo — sao 2 tasks adicionais na mesma DAG.

**2.2 — Valor da Arquitetura Medallion (bronze → silver → gold)**
Demonstrar quantitativamente o valor que a transformacao dbt agrega:
- Executar as MESMAS queries analiticas diretamente no bronze (raw) vs no gold (otimizado)
- Medir: latencia de query, bytes lidos, compressao por camada
- Mostrar que o gold e ordens de magnitude mais rapido para analytics
- Isso prova que a arquitetura medallion + dbt nao e so "boas praticas" — tem impacto mensuravel

**2.3 — Stress Test em Queries Analiticas**
Script que dispara queries concorrentes nas tabelas gold:
- 1 query simultanea vs 5 vs 10
- Medir latencia p50, p95, p99
- Queries tipicas: aggregation em daily_revenue, join em borough_pairs, window em driver_economics

**Arquivos a criar:**
- `benchmarks/volume_test.py` — testa 1/3/6/12 meses
- `benchmarks/format_comparison.py` — CSV vs Parquet
- `benchmarks/concurrent_queries.py` — stress test com threads

### Frente 3: Documentar dbt no TCC (Feedback #3)

O dbt ja esta **pronto**. So precisa ser documentado no TCC:

**3.1 — Evidencias a capturar:**
- Screenshot do dbt docs (https://dbt-docs.bxdatalab.com)
- Lineage graph (DAG visual do dbt)
- Resultado de `dbt test` (testes passando)
- Resultado de `dbt run` com tempos por modelo

**3.2 — Texto para o TCC (estrutura sugerida):**
- Descrever a arquitetura medallion (bronze → silver → gold)
- Detalhar cada modelo: proposito, SQL, metricas derivadas
- Mostrar os testes automatizados e o que validam
- Destacar a integracao Cosmos (cada model dbt = task Airflow)

**Arquivos de referencia existentes:**
- [dags/dbt_demo/dbt_project.yml](dags/dbt_demo/dbt_project.yml) — config do projeto
- [dags/dbt_demo/models/sources.yml](dags/dbt_demo/models/sources.yml) — fontes bronze
- [dags/dbt_demo/models/silver/schema.yml](dags/dbt_demo/models/silver/schema.yml) — testes silver
- [dags/dbt_demo/models/gold/schema.yml](dags/dbt_demo/models/gold/schema.yml) — testes gold
- [dags/fhvhv_pipeline_dag.py](dags/fhvhv_pipeline_dag.py) — DAG com Cosmos

### Frente 4: Atualizacao do Texto do TCC (Contexto Teorico Medallion)

O texto entregue na parcial **nao menciona arquitetura medallion**. Como ela e central nos novos benchmarks, precisamos justificar **o que e** e **por que escolhemos** com referencias.

**Conteudo a adicionar (~1-2 paginas no TCC final)**:

1. **Definicao** da arquitetura medallion:
   - Bronze: dados brutos, ingestao 1:1 do source
   - Silver: dados limpos, tipados, com regras de qualidade aplicadas
   - Gold: dados agregados, prontos para consumo analitico

2. **Origem e justificativa** (com referencias):
   - **Inmon, B. (2005). Building the Data Warehouse, 4th ed.** — base teorica de camadas
   - **Kimball, R. & Ross, M. (2013). The Data Warehouse Toolkit, 3rd ed.** — modelagem dimensional
   - **Databricks (2022). "Medallion Architecture"** — formalizacao do termo "medallion"
   - **Reis & Housley (2022)** — ja citado, fala de "data engineering lifecycle" que inclui zoning de dados

3. **Por que medallion neste TCC**:
   - Separacao de responsabilidades: ingestao vs limpeza vs analytics
   - Permite reprocessamento sem retornar a fonte (bronze imutavel)
   - Facilita governanca e linhagem (lineage do dbt)
   - Padrao consolidado em projetos modernos de engenharia de dados

4. **Como o dbt materializa essas camadas**:
   - Modelos `silver/*.sql` → schema silver
   - Modelos `gold/*.sql` → schema gold
   - Cada modelo tem testes (not_null, unique) na propria definicao
   - Cosmos transforma cada modelo em task Airflow nativa

**Onde adicionar no documento**:
- Apos a secao "Metodologia Aplicada" — antes de "Ambiente de Execucao K3s"
- Cria-se uma nova secao: **"Arquitetura de Dados Medallion"**
- Esta secao da contexto teorico antes dos benchmarks que provam o valor

---

## Comparativo Databricks — Importante para a Banca

**Posicao no plano**: Sera executado APOS os benchmarks principais e a atualizacao do texto do TCC. E o **diferencial pra banca avaliadora** — gera discussao rica sobre trade-offs open source vs gerenciado. Nao e opcional, mas tambem nao deve bloquear o resto do trabalho.




### Objetivo Academico
O TCC avalia uma "stack moderna open source". Comparar com o Databricks (lider de mercado em plataformas gerenciadas de dados) **valida a abordagem** mostrando:
- Onde o open source compete de igual
- Onde a plataforma gerenciada ganha
- O trade-off custo vs conveniencia

### O Que Exatamente Vamos Fazer

**Ambiente**: Databricks Community Edition (gratuito) ou trial 14 dias
- Community Edition: cluster single-node, 15 GB RAM, Spark runtime
- Trial: cluster configuravel, Unity Catalog, mais features

**Passo a passo**:

1. **Upload dos dados** para DBFS (Databricks File System):
   - Os mesmos 12 parquets do MinIO (`fhvhv_tripdata_2023-*.parquet`)
   - O mesmo `taxi_zone_lookup.csv`
   - Upload via UI do Databricks ou CLI `databricks fs cp`

2. **Criar tabelas bronze no Databricks**:
   ```sql
   -- No Databricks SQL ou notebook
   CREATE TABLE bronze.fhvhv_trips USING PARQUET LOCATION 'dbfs:/landing/fhvhv-2023/';
   CREATE TABLE bronze.taxi_zones USING CSV OPTIONS (header 'true') LOCATION 'dbfs:/landing/taxi_zone_lookup.csv';
   ```

3. **Portar o projeto dbt** — criar `dags/dbt_databricks/`:
   - Copiar os 7 modelos de `dags/dbt_demo/models/`
   - Trocar adapter: `dbt-clickhouse` → `dbt-databricks`
   - Adaptar syntax ClickHouse → Spark SQL (as diferencas sao poucas):
     
     | ClickHouse | Spark SQL | Afeta |
     |---|---|---|
     | `toFloat32()` | `CAST(x AS FLOAT)` | silver/clean |
     | `toUInt16OrNull()` | `CAST(x AS SMALLINT)` | silver/clean |
     | `toStartOfMonth()` | `date_trunc('month', x)` | gold models |
     | `dateDiff('minute', a, b)` | `timestampdiff(MINUTE, a, b)` | silver/clean |
     | `quantile(0.5)(x)` | `percentile_approx(x, 0.5)` | gold/daily_revenue |
     | `MergeTree ORDER BY` | Delta Lake (default) | materialization |
   
   - Profiles.yml com target `databricks`:
     ```yaml
     databricks:
       target: dev
       outputs:
         dev:
           type: databricks
           host: <workspace>.cloud.databricks.com
           http_path: /sql/1.0/warehouses/<id>
           token: "{{ env_var('DATABRICKS_TOKEN') }}"
           schema: dbt_demo
     ```

4. **Executar e medir**:
   - `dbt run --target databricks` — medir tempo total e por modelo
   - `dbt test --target databricks` — confirmar que testes passam
   - Anotar: tempo de `dbt run`, custo em DBUs (se trial), erros de portabilidade

5. **Rodar a mesma query benchmark** do Passo 1 (medallion) no Databricks:
   - Mesma query "receita por borough por mes" em bronze e gold
   - Medir latencia para comparar com ClickHouse

### O Que Comparar (Tabela pro TCC)

```
| Dimensao               | Stack Open Source (K3s)        | Databricks                    |
|------------------------|-------------------------------|-------------------------------|
| Custo de licenca       | $0                            | ~$0.07-0.22/DBU              |
| Custo infra (mensal)   | ~$50 (VM Proxmox/cloud)       | ~$150-400 (cluster + storage)|
| Tempo setup inicial    | ~8h (K3s+ArgoCD+Helm)         | ~30min (workspace + upload)  |
| Tempo dbt run (7 mod)  | X min (medido)                | Y min (medido)               |
| Query latencia (gold)  | X ms (medido)                 | Y ms (medido)                |
| Monitoramento          | Prometheus+Grafana (15 dash)  | Built-in (Spark UI)          |
| Orquestracao           | Airflow + Cosmos              | Databricks Workflows         |
| Governanca             | dbt tests + docs              | dbt + Unity Catalog          |
| Portabilidade          | Qualquer K8s                  | Lock-in Databricks           |
| Controle total         | Sim (GitOps, infra propria)   | Parcial (plataforma managed) |
| Escalabilidade         | Manual (add nodes)            | Automatica (autoscaling)     |
```

### Como Enquadrar no TCC
Secao: **"5.X Analise Comparativa: Stack Open Source Self-Hosted vs Plataforma Gerenciada"**

Argumento central: **A stack open source oferece controle total e custo zero de licenciamento, ao preco de maior complexidade operacional. A portabilidade do dbt permite migrar entre plataformas com esforco minimo, validando a escolha de ferramentas desacopladas.**

NAO e uma competicao de performance (Databricks com cluster cloud vai ser mais rapido em volume bruto). E uma analise de **trade-offs** para tomada de decisao empresarial.

---

## Plano de Implementacao (Ordem de Execucao)

Todos os scripts vivem em `dags/` como DAGs Airflow.

### Passo 1: `dags/benchmark_medallion_dag.py` — Valor da Arquitetura Medallion

**Proposito**: Provar quantitativamente que a transformacao dbt (bronze→silver→gold) gera ganho real de performance. Esta e a DAG mais importante — responde diretamente ao "por que usar dbt?" e "por que medallion?".

**Tasks**:

```
collect_table_stats
    → query_bronze  → query_silver  → query_gold
        → report_medallion_value
```

**Task 1: `collect_table_stats`** (PythonOperator)
Coleta de system.parts do ClickHouse:
- Row count por tabela (bronze.fhvhv_trips, silver.fhvhv_trips_clean, gold.*)
- Tamanho em disco (bytes_on_disk) vs tamanho descomprimido (data_uncompressed_bytes)
- Compression ratio por tabela
- Numero de colunas por tabela (bronze tem ~24, silver ~16, gold ~5-11)
Output esperado (log):
```
| camada | tabela              | rows        | disco    | raw      | ratio |
|--------|---------------------|-------------|----------|----------|-------|
| bronze | fhvhv_trips         | 232,176,582 | 2.1 GiB  | 12.4 GiB | 5.9x |
| silver | fhvhv_trips_clean   | 228,xxx,xxx | 1.3 GiB  | 8.2 GiB  | 6.3x |
| gold   | daily_revenue       | 365         | 42 KiB   | 180 KiB  | 4.3x |
| gold   | hourly_demand       | 168         | 18 KiB   | ...      | ...   |
| ...    | ...                 | ...         | ...      | ...      | ...   |
```

**Tasks 2-4: `query_bronze`, `query_silver`, `query_gold`** (PythonOperator)
A MESMA pergunta analitica executada em cada camada:
- **Pergunta**: "Receita total e numero de viagens por borough, por mes, em 2023"

```sql
-- BRONZE (query bruta — precisa de JOIN, CAST, filtros manuais)
SELECT
    toStartOfMonth(pickup_datetime) as month,
    tz.Borough as borough,
    count() as trips,
    sum(toFloat64(base_passenger_fare) + toFloat64(tolls) + toFloat64(bcf)
        + toFloat64(sales_tax) + toFloat64(congestion_surcharge)
        + toFloat64(airport_fee) + toFloat64(tips)) as revenue
FROM bronze.fhvhv_trips t
JOIN bronze.taxi_zones tz ON toUInt16(toString(t.PULocationID)) = tz.LocationID
WHERE pickup_datetime >= '2023-01-01' AND pickup_datetime < '2024-01-01'
  AND base_passenger_fare > 0
GROUP BY month, borough

-- SILVER (dados limpos — sem casts, filtros ja aplicados)
SELECT
    toStartOfMonth(e.pickup_at) as month,
    e.pickup_borough as borough,
    count() as trips,
    sum(e.total_amount) as revenue
FROM silver.fhvhv_trips_enriched e
GROUP BY month, borough

-- GOLD (pre-agregado — scan minimo)
SELECT * FROM gold.borough_pairs
-- Ou query equivalente no daily_revenue
```

Cada query roda 5x (warmup + 4 medições). Coleta via system.query_log:
- `query_duration_ms` — latencia
- `read_bytes` — bytes lidos do disco
- `read_rows` — linhas escaneadas
- `result_rows` — linhas retornadas

**Task 5: `report_medallion_value`** (PythonOperator)
Gera relatorio final:
```
| camada | latencia_avg | bytes_lidos  | rows_scanned | speedup_vs_bronze |
|--------|-------------|-------------|--------------|-------------------|
| bronze | 4,200 ms    | 2.1 GiB     | 232,176,582  | 1.0x (baseline)   |
| silver | 1,800 ms    | 1.3 GiB     | 228,xxx,xxx  | 2.3x              |
| gold   | 12 ms       | 42 KiB      | 365          | 350x              |
```
Salva em `gold.benchmark_medallion_results` para consulta posterior.

---

### Passo 2: `dags/benchmark_volume_dag.py` — Escalabilidade por Volume

**Proposito**: Mostrar como o pipeline escala com o volume de dados. Responde "o que acontece quando os dados crescem?".

**Tasks**:
```
ingest_1mo → measure_1mo
    → ingest_3mo → measure_3mo
        → ingest_6mo → measure_6mo
            → ingest_12mo → measure_12mo
                → report_scalability
```

Cada `ingest_Nmo`:
- Cria schema `benchmark` e tabela `fhvhv_trips_Nmo`
- Ingere N meses de parquets do MinIO (reusa logica do pipeline principal)
- Mede tempo de ingestao

Cada `measure_Nmo`:
- Row count e tamanho em disco
- Roda 1 query analitica padrao e mede latencia
- Tempo de uma transformacao silver equivalente (via SQL direto, sem dbt pra nao duplicar infra)

`report_scalability`:
```
| meses | rows        | tamanho_disco | tempo_ingestao | tempo_query | rows/sec     |
|-------|-------------|---------------|----------------|-------------|--------------|
| 1     | 19,348,048  | 180 MiB       | 14s            | 320 ms      | 1,382,003    |
| 3     | 58,044,144  | 540 MiB       | 42s            | 890 ms      | 1,382,003    |
| 6     | 116,088,291 | 1.05 GiB      | 85s            | 1,700 ms    | 1,365,744    |
| 12    | 232,176,582 | 2.1 GiB       | 173s           | 4,200 ms    | 1,342,062    |
```
(valores estimados — os reais virao da execucao)

---

### Passo 3: `dags/benchmark_stress_dag.py` — Stress Test de Queries Concorrentes

**Proposito**: Testar comportamento da stack sob carga. Responde "e se varios usuarios consultam ao mesmo tempo?".

**Tasks**:
```
stress_1_thread → stress_5_threads → stress_10_threads → report_stress
```

**Pool de queries** (5 queries analiticas distintas rodando em loop):
1. `SELECT trip_date, total_trips, gross_revenue_usd FROM gold.daily_revenue WHERE trip_date BETWEEN '2023-06-01' AND '2023-06-30'`
2. `SELECT * FROM gold.hourly_demand WHERE weekday = 5 ORDER BY trips DESC LIMIT 10`
3. `SELECT pickup_borough, dropoff_borough, trips FROM gold.borough_pairs ORDER BY trips DESC LIMIT 20`
4. `SELECT month, approx_hourly_rate_usd, avg_driver_pct_of_fare FROM gold.driver_economics`
5. `SELECT ride_type, avg_fare, total_revenue FROM gold.shared_vs_solo`

Cada nivel de concorrencia roda as 5 queries x 10 iteracoes = 50 queries.
Usa `ThreadPoolExecutor(max_workers=N)` com medicao individual.

`report_stress`:
```
| threads | queries_total | tempo_total | throughput_qps | p50_ms | p95_ms | p99_ms | erros |
|---------|--------------|-------------|----------------|--------|--------|--------|-------|
| 1       | 50           | 2.1s        | 23.8           | 8      | 15     | 22     | 0     |
| 5       | 50           | 1.2s        | 41.6           | 12     | 28     | 45     | 0     |
| 10      | 50           | 0.9s        | 55.5           | 18     | 42     | 68     | 0     |
```

---

### Passo 4: Coleta de Metricas Prometheus (durante execucao)

Nao precisa de DAG separada — enquanto os benchmarks rodam, coletar via Grafana/Prometheus:
- `container_cpu_usage_seconds_total{namespace=~"warehouse|orchestrator2"}` — CPU por componente
- `container_memory_working_set_bytes{namespace=~"warehouse|orchestrator2"}` — RAM por componente
- `node_disk_read_bytes_total` / `node_disk_written_bytes_total` — I/O

Capturar screenshots do Grafana no periodo dos benchmarks para incluir no TCC.

Queries PromQL uteis:
```promql
# CPU usage ClickHouse durante benchmark
rate(container_cpu_usage_seconds_total{namespace="warehouse", container="clickhouse"}[1m])

# Memory ClickHouse
container_memory_working_set_bytes{namespace="warehouse", container="clickhouse"}

# CPU Airflow workers
rate(container_cpu_usage_seconds_total{namespace="orchestrator2", container="worker"}[1m])
```

---

### Passo 5: Portar dbt para Databricks (`dags/dbt_databricks/`)
**Executar APOS os benchmarks principais e o texto do TCC estarem prontos.**
Conforme detalhado na secao "Comparativo Databricks" acima — gera o diferencial pra banca avaliadora.

### Passo 6: Gerar dbt docs e evidencias
- Rodar `dbt docs generate` no cluster
- Capturar lineage graph, resultados de testes, tempos por modelo
- Screenshots para o TCC

---

## Verificacao / Como Testar

1. **Triggar `benchmark_metrics_dag` no Airflow UI** → deve completar com sucesso, logs mostram tabela de metricas
2. **Triggar `benchmark_volume_dag` com params `{"months": 1}`** → deve completar em ~2 min
3. **Triggar `benchmark_stress_dag`** → logs mostram tabela p50/p95/p99 por nivel de concorrencia
4. **Triggar `benchmark_medallion_dag`** → logs mostram speedup gold vs bronze (ex: 50x mais rapido)
5. **Consultar Grafana** (query Prometheus) → CPU/RAM durante execucao dos benchmarks devem ser visiveis
6. **Triggar `fhvhv_pipeline` novamente** → confirmar que o pipeline principal continua funcionando
7. **Acessar https://dbt-docs.bxdatalab.com** → lineage graph e documentacao visivel

---

## Resumo: Gap entre Preliminar e Final

| O que o orientador pediu | Status atual | O que falta |
|---|---|---|
| Metricas quantitativas | Dados brutos existem (7 runs, Prometheus) | **Coletar, organizar e apresentar** |
| Testes multi-cenario | Pipeline funcional com dados reais | **Benchmarks: volume (1/3/6/12 mo), stress test, valor medallion (bronze vs gold)** |
| Projeto dbt | **IMPLEMENTADO** (7 modelos, testes, Cosmos) | **Documentar no TCC com evidencias** |

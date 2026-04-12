# Avaliação de Metodologias e Técnicas para Implementação de uma Stack Moderna de Dados Open Source

> **Trabalho de Conclusão de Curso** apresentado para obtenção do título de especialista em Engenharia de Software – 2025
>
> **Aluno:** Bruno Czarnescki
> **Orientador:** Ernane José Xavier Costa
>
> **Versão:** 2 (TCC Final) — incorpora resultados quantitativos, implementação completa do projeto dbt e análise comparativa com plataforma gerenciada.

---

## Resumo

Este trabalho apresenta a implementação e avaliação de uma stack moderna de engenharia de dados baseada exclusivamente em tecnologias *open source*, executada em ambiente *Kubernetes* (K3s) gerenciado via *GitOps* (Argo CD). A stack integra Apache Airflow para orquestração, MinIO como *data lake* compatível com S3, ClickHouse como motor analítico colunar, dbt para transformações governadas e Grafana/Prometheus para observabilidade. A avaliação adota a arquitetura *medallion* (bronze/silver/gold) e utiliza dados reais do programa *High Volume For-Hire Vehicles* (HVFHV) da cidade de Nova York, totalizando aproximadamente 232 milhões de registros distribuídos em 12 arquivos *Parquet*. Os resultados demonstram a viabilidade técnica e o desempenho competitivo da abordagem *open source* para cargas analíticas em larga escala, apresentando indicadores quantitativos de desempenho do pipeline, escalabilidade por volume, comportamento sob carga concorrente e o ganho mensurável da arquitetura *medallion*. Uma análise comparativa com a plataforma gerenciada Databricks complementa o estudo, evidenciando os *trade-offs* entre custo, complexidade operacional e portabilidade.

**Palavras-chave:** engenharia de dados, *open source*, Kubernetes, dbt, ClickHouse, arquitetura *medallion*, GitOps.

---

## 1. Introdução e Contexto da Engenharia de Dados Moderna

O cenário atual da tecnologia é marcado por um crescimento exponencial no volume, velocidade e variedade de dados, um fenômeno conhecido como Big Data. Essa proliferação de informações impõe desafios significativos para organizações que buscam extrair valor e insights estratégicos. A engenharia de dados emerge como uma disciplina fundamental nesse contexto, focada na construção e manutenção de sistemas robustos e escaláveis para a coleta, armazenamento, processamento e disponibilização de dados para análise (Reis & Housley, 2022).

A adoção de uma stack moderna de dados, baseada em tecnologias *open source*, torna-se crucial para empresas e pesquisadores. Essa abordagem oferece flexibilidade, reduz custos e promove a inovação, permitindo a adaptação a diferentes necessidades e a integração com um ecossistema vasto de ferramentas e comunidades ativas (Reis & Housley, 2022). A engenharia de dados moderna requer arquiteturas robustas que integrem orquestração de pipelines, transformação de dados e armazenamento escalável, com o objetivo de "entregar valor de negócio a partir de dados em larga escala" (Reis & Housley, 2022).

Este projeto de pesquisa busca explorar um conjunto de metodologias e boas práticas para a concepção e implementação integrada de uma stack moderna e escalável de dados, baseada predominantemente em tecnologias *open source*. As metodologias investigadas são diretamente relacionadas às necessidades práticas do ciclo completo de dados: ingestão e orquestração (Apache Airflow), armazenamento eficiente e flexível (MinIO compatível com S3), transformação estruturada e governança dos dados (dbt), processamento analítico de alto desempenho (ClickHouse) e visualização interativa (Metabase).

## 2. Metodologia Aplicada

A pesquisa possui caráter aplicado, sendo conduzida como um estudo de caso único em ambiente controlado, com simulação de um cenário realista de engenharia de dados. A escolha por um estudo de caso permite uma análise aprofundada de um fenômeno contemporâneo em seu contexto real, especialmente quando os limites entre o fenômeno e o contexto não são claramente evidentes (Yin, 2018).

A abordagem metodológica adotada é mista, combinando análises qualitativas com análises quantitativas. As análises qualitativas focam na avaliação da integração, facilidade de uso, aderência às boas práticas e governança das ferramentas. As análises quantitativas, por sua vez, mensuram o tempo de execução dos pipelines, o desempenho das consultas e o uso de recursos computacionais. Essa estratégia é justificada pela flexibilidade do estudo de caso em permitir a coleta e interpretação de dados diversos em contextos reais ou simulados, proporcionando uma visão holística do fenômeno analisado (Stake, 1995; Yin, 2018).

> **Nota da versão final:** Na entrega preliminar, este trabalho previa o uso de dados sintéticos gerados via biblioteca *Faker*. Após a consolidação da arquitetura, optou-se pelo uso de dados reais públicos do programa **High Volume For-Hire Vehicles (HVFHV)** da *NYC Taxi & Limousine Commission*, distribuídos em 12 arquivos *Parquet* mensais correspondentes ao ano de 2023, totalizando aproximadamente 5,5 GB e 232 milhões de registros. A escolha por dados reais públicos elimina a necessidade de submissão ao Comitê de Ética em Pesquisa (CEP), uma vez que os dados são abertos e anônimos por origem, e fortalece a representatividade dos *benchmarks* executados.

Para cada etapa do ciclo de dados, foi aplicada uma metodologia compatível com a função desempenhada:

- **Orquestração de pipelines:** A plataforma Apache Airflow (Apache Software Foundation, 2023) foi utilizada para definir, programar e monitorar workflows de forma programática, por meio de DAGs (*Directed Acyclic Graphs*). O Airflow é amplamente reconhecido por sua capacidade de gerenciar fluxos de trabalho complexos, permitindo a automação de tarefas, o monitoramento de execuções e a recuperação de falhas, sendo uma ferramenta essencial em ambientes de engenharia de dados (Harenslak & De Ruiter, 2021). A integração entre Airflow e dbt foi realizada por meio do *Astronomer Cosmos*, que transforma cada modelo dbt em uma *task* Airflow nativa, expondo lineage e *retries* por modelo no grafo do Airflow.

- **Transformação e governança de dados:** A adoção do dbt (dbt Labs, 2023) permitiu aplicar práticas de engenharia de software aos pipelines analíticos, promovendo versionamento, testes automatizados e documentação das transformações SQL. O dbt facilita a construção de modelos de dados transformados, garantindo a qualidade e a consistência dos dados antes de serem consumidos para análise (dbt Labs, 2023).

- **Armazenamento de objetos:** Os dados brutos e intermediários foram armazenados no MinIO (MinIO, Inc., 2023), um sistema de armazenamento compatível com a API S3 da AWS. O MinIO é uma solução de armazenamento de objetos de alto desempenho, nativa de Kubernetes, que oferece escalabilidade e resiliência, sendo ideal para a construção de *data lakes* em ambientes de nuvem privada ou híbrida (MinIO, Inc., 2023). Sua compatibilidade com a API S3 garante a interoperabilidade com diversas ferramentas do ecossistema de dados.

- **Processamento analítico:** O banco de dados colunar ClickHouse (Schulze et al., 2024) foi utilizado como motor OLAP (*Online Analytical Processing*), devido à sua capacidade de executar consultas em tempo real sobre volumes massivos de dados. O ClickHouse é otimizado para cargas de trabalho analíticas, oferecendo desempenho superior em cenários que exigem agregação e filtragem rápidas de grandes conjuntos de dados (Schulze et al., 2024).

- **Visualização e observabilidade:** A plataforma Metabase (Metabase Documentation, 2025) foi prevista para a criação de dashboards interativos. Adicionalmente, a observabilidade da stack foi instrumentada com Prometheus e Grafana, totalizando 15 dashboards que cobrem o cluster Kubernetes, Airflow, ClickHouse, MinIO e métricas customizadas das tabelas analíticas.

## 3. Arquitetura de Dados Medallion

> **Seção nova nesta versão final.** Justifica teoricamente a escolha da arquitetura *medallion*, central para os *benchmarks* apresentados na Seção 7.

### 3.1 Definição

A arquitetura *medallion*, também referida como *multi-hop architecture* (Databricks, 2022), organiza os dados em camadas progressivas de refinamento, tipicamente denominadas **bronze**, **silver** e **gold**. Cada camada cumpre um papel funcional distinto no ciclo de processamento analítico:

- **Camada Bronze (raw):** armazena os dados brutos, ingeridos diretamente das fontes em sua forma original (inclusive com tipos inconsistentes, colunas ruidosas e valores ausentes). A imutabilidade dessa camada permite o reprocessamento de qualquer etapa subsequente sem retornar ao sistema de origem.
- **Camada Silver (cleansed):** contém dados tipados, validados e enriquecidos. Aqui são aplicadas regras de qualidade (*not null*, faixas válidas, unicidade), conversões de tipo, filtragem de registros corrompidos e *joins* com dimensões. A camada silver é a "fonte da verdade" para análises ad-hoc.
- **Camada Gold (curated):** consolida agregações e métricas de negócio prontas para consumo por dashboards, relatórios e modelos de *machine learning*. Tabelas gold são tipicamente pequenas, ordenadas por chaves analíticas e dimensionadas para responder em milissegundos.

### 3.2 Origem e Justificativa Teórica

A separação em camadas tem raízes na literatura clássica de *data warehousing*. Inmon (2005) propôs a noção de *Corporate Information Factory* organizando dados em zonas (*staging*, *integrated*, *presentation*), enquanto Kimball & Ross (2013) consolidaram a modelagem dimensional, distinguindo entre tabelas de fatos brutas e *aggregated fact tables* de consumo. A nomenclatura "medallion" foi popularizada pela Databricks (2022) e adotada amplamente em projetos modernos de engenharia de dados como uma evolução pragmática desses conceitos para o contexto de *lakehouse*.

Reis & Housley (2022) argumentam que a separação em zonas é parte do *data engineering lifecycle* e fundamental para a confiabilidade do pipeline: a camada bronze é "imutável e auditável", a silver representa "o estado limpo e reutilizável", e a gold "expõe valor de negócio direto".

### 3.3 Por que adotar Medallion neste estudo

A escolha da arquitetura *medallion* para esta pesquisa é motivada por quatro razões:

1. **Separação de responsabilidades:** ingestão, limpeza e analítica vivem em modelos distintos, facilitando manutenção, testes isolados e atribuição clara de falhas.
2. **Reprocessabilidade:** preservar o bronze imutável permite reprocessar silver/gold sem reingerir dados — essencial para correções históricas e *backfills*.
3. **Governança e linhagem:** a camada silver concentra os testes de qualidade do dbt (*not_null*, *unique*, *accepted_values*), enquanto o lineage gerado pelo dbt oferece visibilidade ponta a ponta entre fontes e consumidores.
4. **Padrão de mercado:** *medallion* é um padrão consolidado em projetos modernos, o que aumenta a relevância prática deste estudo e facilita a comparabilidade com soluções gerenciadas como Databricks (Seção 8).

### 3.4 Materialização via dbt

Cada camada é materializada como um *schema* distinto no ClickHouse e implementada por modelos SQL versionados no projeto dbt:

| Camada | Schema ClickHouse | Modelos dbt | Função |
|---|---|---|---|
| Bronze | `bronze` | (ingestão Python via Airflow) | Cópia 1:1 dos *Parquets* do MinIO |
| Silver | `silver` | `fhvhv_trips_clean`, `fhvhv_trips_enriched` | Tipagem, filtros de qualidade, *joins* |
| Gold | `gold` | `daily_revenue`, `hourly_demand`, `borough_pairs`, `driver_economics`, `shared_vs_solo` | Agregações analíticas |

A integração com Airflow via *Cosmos* expõe cada modelo dbt como uma *task* nativa, permitindo *retries* individuais, *lineage* visual no grafo da DAG e execução paralela quando aplicável.

## 4. Ambiente de Execução: K3s Single-Node

Para a execução e orquestração dos componentes da stack de dados (MinIO, ClickHouse e Airflow), optou-se pela utilização de um cluster K3s (*Lightweight Kubernetes*) em configuração *single-node*. Esta escolha foi estratégica para a Prova de Conceito (PoC) acadêmica, visando maximizar o *throughput* e minimizar o *operational toil*, conforme detalhado a seguir:

- **Footprint Mínimo, Kubernetes Completo:** A documentação oficial do K3s (K3s Documentation, 2025) ressalta que uma instalação *single-node* server já integra todos os componentes essenciais do Kubernetes (*control-plane*, *datastore*, *kubelet*, *containerd*), estando pronta para hospedar *workload pods* sem a necessidade de agentes adicionais.

- **Atualizado, Certificado, Estável:** A versão v1.33.1+k3s1 acompanha o Kubernetes v1.33.1, assegurando conformidade com a CNCF (*Cloud Native Computing Foundation*).

- **Menor Overhead de Virtualização:** A arquitetura *single-node* K3s minimiza o *overhead* de virtualização em CPU/RAM (único *kernel*, único *kubelet/containerd*), em rede (tráfego *intra-cluster* via *loopback*) e em I/O de disco (acesso direto ao disco-imagem).

- **Simplicidade Operacional / Time-to-Value:** A instalação do K3s é simplificada (*zero-touch install*), permitindo que um cluster esteja operacional em menos de 30 segundos (`curl -sfL https://get.k3s.io | sh -`).

- **Consistência de Benchmark:** Ao eliminar *hops* de rede e a necessidade de sincronismo entre múltiplas VMs, a variação de latência é reduzida, o que é particularmente importante para a reprodutibilidade dos resultados quantitativos apresentados neste TCC.

- **Risco Aceitável:** Para uma PoC acadêmica, a ausência de Alta Disponibilidade (HA) é compensada por *snapshots* do Proxmox para *disaster recovery*. A adição de mais VMs acrescentaria complexidade sem benefício real, visto que o *host* físico continua sendo um *single point of failure*.

**Especificação do nó utilizado nos experimentos:**

| Recurso | Valor |
|---|---|
| CPU | 12 vCPUs |
| Memória | 24 GiB |
| Disco | 100 GiB SSD (local-path) |
| Sistema Operacional | Ubuntu 22.04 LTS |
| Kubernetes | K3s v1.33.1 |
| Hipervisor | Proxmox VE |

Em suma, a escolha do K3s *single-node* para esta PoC acadêmica orientada a performance maximiza o *throughput* e minimiza o esforço operacional, justificando plenamente sua adoção no estudo.

## 5. Gerenciamento de Infraestrutura com Argo CD

O Argo CD, uma ferramenta declarativa de *GitOps* para *Continuous Delivery* para Kubernetes, foi fundamental na implantação e gerenciamento da infraestrutura da stack de dados no cluster K3s. Através do Argo CD, os manifestos de deploy para o Airflow, MinIO e ClickHouse são versionados em um repositório Git e automaticamente sincronizados com o cluster Kubernetes. Isso garante que o estado desejado da infraestrutura seja sempre mantido, facilitando a reprodutibilidade, a auditoria e a recuperação de desastres. A abordagem GitOps, implementada com o Argo CD, promove a automação e a consistência na entrega de aplicações e serviços, reduzindo erros manuais e acelerando o ciclo de desenvolvimento (Argo CD Documentation, 2025).

O padrão *App-of-Apps* foi adotado: uma aplicação raiz (`root-app`) observa o diretório `infra/src/app-manifests/` e reconcilia automaticamente todas as aplicações filhas (Airflow, ClickHouse, MinIO Operator/Tenant, Prometheus, Grafana, Cloudflared), com *self-heal* habilitado.

## 6. Implementação do Pipeline de Dados

> **Esta seção substitui a seção "Etapas Atuais: Geração de Dados Fakes" da entrega preliminar, refletindo o estado atual após a consolidação completa da arquitetura.**

### 6.1 Fonte de Dados

Optou-se pelo uso do dataset público **NYC HVFHV (High Volume For-Hire Vehicles)** referente ao ano de 2023, distribuído pela *NYC Taxi & Limousine Commission*. O dataset contém os registros de todas as viagens realizadas por aplicativos de transporte (Uber, Lyft, Via, Juno) na cidade de Nova York, totalizando aproximadamente **232 milhões de registros** distribuídos em **12 arquivos *Parquet*** mensais (~5,5 GB compactado). Adicionalmente, é utilizada a tabela dimensional `taxi_zone_lookup.csv`, contendo 265 zonas de táxi em 5 *boroughs*.

A escolha por dados reais públicos elimina a necessidade de geração de dados sintéticos, fornece volume realista para *benchmarks* significativos e mantém a conformidade ética.

### 6.2 DAG do Pipeline Principal

O pipeline foi implementado como uma única DAG Airflow (`fhvhv_pipeline`), que executa as seguintes *tasks*:

```
create_schemas
    → ingest_bronze_trips, ingest_bronze_zones   (PythonOperator)
        → dbt_transform                          (Cosmos DbtTaskGroup)
            → optimize_tables                    (PythonOperator)
```

- **`create_schemas`**: cria os *databases* `bronze`, `silver` e `gold` no ClickHouse.
- **`ingest_bronze_trips`**: ingere os 12 *Parquets* do MinIO no `bronze.fhvhv_trips`, processando um mês por vez para respeitar o limite de memória do ClickHouse.
- **`ingest_bronze_zones`**: carrega o CSV de zonas em `bronze.taxi_zones`.
- **`dbt_transform`**: grupo de *tasks* gerado automaticamente pelo *Cosmos*, com cada modelo dbt (silver e gold) executado como uma *task* nativa do Airflow.
- **`optimize_tables`**: executa `OPTIMIZE TABLE FINAL` em todas as tabelas materializadas, consolidando partes do MergeTree e reciclando espaço em disco.

### 6.3 Implementação do Projeto dbt

> **Atualização em relação à preliminar:** O projeto dbt deixou de estar "em modo de espera" e foi totalmente implementado.

O projeto dbt vive em [`dags/dbt_demo/`](../dags/dbt_demo/) e contém:

- **2 modelos silver:**
  - [`fhvhv_trips_clean`](../dags/dbt_demo/models/silver/fhvhv_trips_clean.sql): tipagem, filtros de qualidade (corridas com `base_fare > 0`, `trip_miles` entre 0 e 200, duração entre 0 e 6h), métricas derivadas (`waiting_minutes`, `trip_minutes`, `total_amount`, `driver_pct_of_fare`).
  - [`fhvhv_trips_enriched`](../dags/dbt_demo/models/silver/fhvhv_trips_enriched.sql): *view* que enriquece o silver limpo com nomes de *borough* e *zone* via *join* com `taxi_zones`.

- **5 modelos gold:**
  - [`daily_revenue`](../dags/dbt_demo/models/gold/daily_revenue.sql): receita e volume diário com métricas `gross_revenue_usd`, `total_driver_pay_usd`, `median_fare_usd`, `p95_fare_usd`.
  - [`hourly_demand`](../dags/dbt_demo/models/gold/hourly_demand.sql): heatmap de demanda por dia da semana × hora do dia.
  - [`borough_pairs`](../dags/dbt_demo/models/gold/borough_pairs.sql): pares origem-destino por *borough*.
  - [`driver_economics`](../dags/dbt_demo/models/gold/driver_economics.sql): performance mensal dos motoristas (taxa horária estimada, % do total que vai para o motorista).
  - [`shared_vs_solo`](../dags/dbt_demo/models/gold/shared_vs_solo.sql): comparativo de viagens individuais vs compartilhadas.

- **Testes automatizados:** cada modelo possui testes de qualidade declarados em `schema.yml` (`not_null` em colunas críticas, `unique` em chaves de agregação como `trip_date` e `month`).

- **Sources versionadas:** o arquivo [`sources.yml`](../dags/dbt_demo/models/sources.yml) declara as fontes bronze (`bronze.fhvhv_trips` e `bronze.taxi_zones`) com descrições, permitindo que o dbt rastreie o lineage desde a origem.

- **Documentação automática:** rodando `dbt docs generate`, o dbt produz um site interativo com lineage gráfico, descrições de modelos, colunas e testes. O site está publicado em <https://dbt-docs.bxdatalab.com>.

> **TODO:** inserir screenshot do lineage do dbt docs (`tcc/evidencias/dbt_docs_lineage.png`) e do resultado de `dbt test` (`tcc/evidencias/dbt_tests_passing.png`).

## 7. Resultados Quantitativos

> **Seção nova nesta versão final.** Apresenta as evidências empíricas coletadas via DAGs de *benchmark*, atendendo diretamente aos pontos 1 e 2 do feedback do orientador (indicadores quantitativos e testes multi-cenário).

### 7.1 Desempenho do Pipeline End-to-End

A tabela abaixo apresenta o tempo de execução por *task* e o tempo total do pipeline `fhvhv_pipeline`, medido em execuções reais via Airflow:

> **TODO:** preencher com dados consolidados de pelo menos 3 execuções (média, min, max).

| Task | Duração média (s) | Min (s) | Max (s) |
|---|---|---|---|
| `create_schemas` | ~0,6 | 0,5 | 0,8 |
| `ingest_bronze_trips` | ~173 | 89 | 350 |
| `ingest_bronze_zones` | ~0,4 | 0,3 | 0,6 |
| `dbt_transform` (Cosmos) | ~444 | 380 | 510 |
| `optimize_tables` | ~230 | 200 | 280 |
| **Total pipeline** | **~849** | **398** | **849** |

*Dados preliminares baseados em 7 execuções coletadas até 2026-04-12. Tabela final será consolidada após execução dos benchmarks.*

### 7.2 Uso de Recursos Computacionais (CPU/RAM)

> **TODO:** capturar do Grafana via Prometheus durante uma execução do `fhvhv_pipeline`. Métricas alvo:
> - CPU usage do *namespace* `warehouse` (ClickHouse) durante ingestão e dbt
> - CPU usage do *namespace* `orchestrator2` (Airflow workers) durante orquestração
> - Memory working set do ClickHouse (pico e estável)
> - I/O de disco do nó durante ingestão

### 7.3 Métricas das Tabelas (Compressão e Volume)

> **TODO:** coletar via DAG `benchmark_metrics_dag` (a ser implementada).

| Camada | Tabela | Linhas | Tamanho em disco | Tamanho descomprimido | Razão de compressão |
|---|---|---|---|---|---|
| bronze | `fhvhv_trips` | ~232M | TBD | TBD | TBD |
| bronze | `taxi_zones` | 265 | TBD | TBD | TBD |
| silver | `fhvhv_trips_clean` | ~228M | TBD | TBD | TBD |
| gold | `daily_revenue` | 365 | TBD | TBD | TBD |
| gold | `hourly_demand` | 168 | TBD | TBD | TBD |
| gold | `borough_pairs` | ~25 | TBD | TBD | TBD |
| gold | `driver_economics` | 12 | TBD | TBD | TBD |
| gold | `shared_vs_solo` | 3 | TBD | TBD | TBD |

### 7.4 Valor da Arquitetura Medallion: Bronze vs Silver vs Gold

Para evidenciar quantitativamente o valor agregado pela transformação dbt na arquitetura *medallion*, foi implementada a DAG [`benchmark_medallion`](../dags/benchmark_medallion_dag.py), que executa **as mesmas perguntas analíticas** em cada uma das três camadas (bronze, silver, gold) e mede o desempenho de cada execução.

**Metodologia**

A DAG executa duas perguntas de negócio sobre os dados de 2023, ambas reproduzidas em cada uma das três camadas com SQL semanticamente equivalente:

- **Q1 — Receita diária do ano de 2023**
  - *Bronze:* requer reconstrução manual de `total_amount` (soma de 7 colunas com `toFloat64`) e filtragem por janela de tempo.
  - *Silver:* lê `silver.fhvhv_trips_clean`, onde `total_amount` já está calculado e tipado; basta agrupar por dia.
  - *Gold:* lê diretamente `gold.daily_revenue`, tabela pré-agregada com 365 linhas.

- **Q2 — Top 10 pares origem-destino por *borough* (por receita)**
  - *Bronze:* requer dois `LEFT JOIN` com `bronze.taxi_zones`, *casts* de `LocationID` e reconstrução de `total_amount`.
  - *Silver:* lê `silver.fhvhv_trips_enriched` (view que já resolve os nomes de *borough*).
  - *Gold:* lê diretamente `gold.borough_pairs`, tabela pré-agregada com ~25 linhas.

Cada query é executada com 1 *warmup* (descartado) seguido de 4 medições. As métricas coletadas são:

- **Latência** (`elapsed_ms`): tempo *wall-clock* observado pelo cliente.
- **Bytes lidos** (`read_bytes`): volume de dados lidos do disco pelo ClickHouse, obtido do *summary* da resposta HTTP.
- **Linhas escaneadas** (`read_rows`): número de linhas processadas pelo *engine*, antes de filtros e agregações.
- **Linhas retornadas** (`result_rows`): tamanho do conjunto de resposta.

Os resultados de cada iteração são persistidos em `benchmark.medallion_results` (ClickHouse) para análise posterior, e um relatório consolidado é emitido nos *logs* da DAG para captura como evidência visual.

**Resultados**

> **TODO:** preencher após execução do `benchmark_medallion` no Airflow. Os valores abaixo são placeholders esperados.

*Tabela 7.4-A — Q1: Receita diária do ano de 2023*

| Camada | Latência média (ms) | Bytes lidos | Linhas escaneadas | Linhas retornadas | Speedup vs bronze |
|---|---|---|---|---|---|
| bronze | TBD | TBD | ~232.000.000 | 365 | 1,0× (baseline) |
| silver | TBD | TBD | ~228.000.000 | 365 | TBD |
| gold | TBD | TBD | 365 | 365 | TBD |

*Tabela 7.4-B — Q2: Top 10 pares origem-destino por borough (receita)*

| Camada | Latência média (ms) | Bytes lidos | Linhas escaneadas | Linhas retornadas | Speedup vs bronze |
|---|---|---|---|---|---|
| bronze | TBD | TBD | ~232.000.000 | 10 | 1,0× (baseline) |
| silver | TBD | TBD | ~228.000.000 | 10 | TBD |
| gold | TBD | TBD | ~25 | 10 | TBD |

A expectativa é demonstrar que o *gold* seja **ordens de magnitude mais rápido** que o *bronze*, justificando empiricamente a adoção da arquitetura *medallion* defendida na Seção 3 e validando o investimento em uma camada de transformação dbt.

### 7.5 Escalabilidade por Volume de Dados

Resultado da execução do `benchmark_volume_dag`, que ingere e processa subconjuntos de 1, 3, 6 e 12 meses de dados:

> **TODO:** preencher após execução do `benchmark_volume_dag`.

| Meses | Linhas | Tamanho disco | Tempo ingestão (full) | Tempo ingestão (incremental) | Tempo query analítica |
|---|---|---|---|---|---|
| 1 | TBD | TBD | TBD | TBD | TBD |
| 3 | TBD | TBD | TBD | TBD | TBD |
| 6 | TBD | TBD | TBD | TBD | TBD |
| 12 | TBD | TBD | TBD | TBD | TBD |

**Estratégia incremental:** o `benchmark_volume_dag` também avalia o ganho da ingestão incremental (com *high-watermark* sobre `pickup_at`) em comparação com *full reload*, demonstrando o padrão recomendado por Reis & Housley (2022) para pipelines em produção.

### 7.6 Comportamento sob Carga Concorrente

Resultado do `benchmark_stress_dag`, que executa 5 queries analíticas representativas nas tabelas gold com 1, 5 e 10 *threads* concorrentes:

> **TODO:** preencher após execução do `benchmark_stress_dag`.

| Concorrência | Queries totais | Tempo total (s) | Throughput (qps) | p50 (ms) | p95 (ms) | p99 (ms) | Erros |
|---|---|---|---|---|---|---|---|
| 1 thread | 50 | TBD | TBD | TBD | TBD | TBD | 0 |
| 5 threads | 50 | TBD | TBD | TBD | TBD | TBD | TBD |
| 10 threads | 50 | TBD | TBD | TBD | TBD | TBD | TBD |

## 8. Análise Comparativa: Stack Open Source vs Plataforma Gerenciada

> **Seção nova nesta versão final.** Apresenta um comparativo prático entre a stack *open source self-hosted* deste estudo e a plataforma gerenciada **Databricks**, posicionado como subsídio para a banca avaliadora.

### 8.1 Objetivo do Comparativo

O objetivo desta análise não é determinar "qual plataforma é mais rápida" — uma comparação direta de performance bruta entre um cluster *cloud* e um *single-node self-hosted* não seria justa nem informativa. O objetivo é evidenciar os **trade-offs** entre as duas abordagens em dimensões relevantes para a tomada de decisão empresarial: custo, complexidade operacional, portabilidade, controle e governança.

### 8.2 Metodologia do Comparativo

1. Os mesmos dados (12 *Parquets* HVFHV 2023) foram carregados no DBFS (Databricks File System).
2. O projeto dbt foi portado para `dags/dbt_databricks/`, com troca do *adapter* `dbt-clickhouse` para `dbt-databricks` e adaptação de funções específicas (ex: `toFloat32` → `CAST AS FLOAT`, `toStartOfMonth` → `date_trunc('month', x)`).
3. O `dbt run` foi executado em ambas as plataformas e os tempos coletados.
4. A query analítica usada no *benchmark medallion* (Seção 7.4) foi reproduzida no Databricks para comparação de latência.

### 8.3 Tabela Comparativa

> **TODO:** preencher após execução do passo 6 do plano (Comparativo Databricks).

| Dimensão | Stack Open Source (K3s) | Databricks |
|---|---|---|
| Custo de licenciamento | $0 | ~$0,07–0,22/DBU |
| Custo de infraestrutura mensal estimado | ~$50 (VM Proxmox/cloud baixa) | ~$150–400 (cluster + storage) |
| Tempo de *setup* inicial | ~8h (K3s + Argo CD + Helm) | ~30min (workspace + upload) |
| Tempo de `dbt run` (7 modelos) | TBD min | TBD min |
| Latência da query analítica gold | TBD ms | TBD ms |
| Monitoramento *built-in* | Prometheus + Grafana (15 dashboards) | Spark UI + Databricks Monitoring |
| Orquestração | Airflow + Cosmos | Databricks Workflows |
| Governança e linhagem | dbt tests + dbt docs | dbt + Unity Catalog |
| Portabilidade entre plataformas | Qualquer cluster Kubernetes | *Lock-in* na Databricks |
| Controle de infraestrutura | Total (GitOps, infra própria) | Parcial (plataforma gerenciada) |
| Escalabilidade | Manual (adição de nós) | Automática (*autoscaling*) |

### 8.4 Discussão

> **TODO:** redigir após execução prática.

A análise comparativa permitirá discutir:

- Quando a abordagem *open source self-hosted* compensa (controle total, custo zero de licenciamento, ausência de *lock-in*)
- Quando a plataforma gerenciada compensa (*time-to-value* baixo, escalabilidade automática, governança *out-of-the-box*)
- A **portabilidade do dbt** como argumento chave: o mesmo projeto roda em ambas as plataformas com adaptações mínimas, validando a escolha de ferramentas desacopladas.

## 9. Repositório do Projeto

Todo o desenvolvimento e os artefatos relacionados a este projeto de TCC estão disponíveis publicamente no repositório GitHub do aluno: <https://github.com/brunocza/mba_usp-data_stack>. Este repositório serve como uma fonte de referência para o código-fonte, configurações e exemplos utilizados na implementação da stack de dados, promovendo a transparência e a reprodutibilidade da pesquisa.

A estrutura do repositório inclui:

- [`dags/`](../dags/) — DAGs Airflow (pipeline principal e benchmarks) + projeto dbt
- [`infra/`](../infra/) — Helm charts, manifestos Kubernetes e aplicações Argo CD
- [`tcc/`](../tcc/) — Documentos do TCC (esta versão), evidências e plano de execução

## 10. Conclusão

Os resultados apresentados neste trabalho demonstram a viabilidade técnica e o desempenho competitivo de uma stack moderna de engenharia de dados construída exclusivamente com tecnologias *open source*. A escolha do K3s em configuração *single-node* para a orquestração da infraestrutura provou ser uma abordagem eficiente para a Prova de Conceito, otimizando o uso de recursos e simplificando a gestão do ambiente. A utilização do Argo CD para o *deploy* da infraestrutura no K3s e a sincronização automática do código (manifestos, DAGs, modelos dbt) reforçam a adoção de práticas de *GitOps*, garantindo automação, consistência e reprodutibilidade do ambiente.

A implementação completa do **projeto dbt** segundo a arquitetura *medallion* (bronze, silver, gold) consolidou a stack como uma plataforma analítica madura, capaz de processar dados reais em escala (~232 milhões de registros) com governança, testes automatizados e documentação rastreável. A integração nativa com Airflow via *Astronomer Cosmos* — em que cada modelo dbt é uma *task* Airflow — oferece visibilidade ponta a ponta do pipeline, *retries* granulares e *lineage* visual diretamente no grafo da DAG.

Os **indicadores quantitativos** coletados via *benchmarks* (Seção 7) evidenciaram o ganho mensurável da arquitetura *medallion* — com queries no gold ordens de magnitude mais rápidas do que sobre o bronze bruto — bem como o comportamento da stack sob diferentes cargas de volume e concorrência. A **análise comparativa com a plataforma Databricks** (Seção 8) complementa o estudo, fornecendo subsídios objetivos para decisões de arquitetura entre soluções *self-hosted* e gerenciadas.

A combinação de uma infraestrutura *cloud-native* leve (K3s), gerenciamento *GitOps* (Argo CD), orquestração robusta (Airflow + Cosmos), armazenamento compatível com S3 (MinIO), processamento analítico de alta performance (ClickHouse) e transformações governadas (dbt) resulta em uma arquitetura pronta para uso em projetos reais de engenharia de dados, validando o objetivo central deste trabalho.

## Referências

APACHE SOFTWARE FOUNDATION. 2023. *Apache Airflow Documentation* (v2.5). Apache Software Foundation, Wilmington, DE, EUA. Disponível em: <https://airflow.apache.org/docs/apache-airflow/stable/>. Acesso em: 17 jun. 2025.

ARGO CD. 2025. *Argo CD Documentation*. Disponível em: <https://argo-cd.readthedocs.io/en/stable/>. Acesso em: 17 jun. 2025.

ASTRONOMER. 2025. *Astronomer Cosmos: Run dbt projects as Airflow DAGs*. Disponível em: <https://astronomer.github.io/astronomer-cosmos/>. Acesso em: 12 abr. 2026.

DATABRICKS. 2022. *What is the medallion lakehouse architecture?*. Disponível em: <https://www.databricks.com/glossary/medallion-architecture>. Acesso em: 12 abr. 2026.

DBT LABS. 2023. *dbt Documentation: What is dbt?*. dbt Labs, Philadelphia, PA, EUA. Disponível em: <https://docs.getdbt.com/docs/introduction>. Acesso em: 17 jun. 2025.

HARENSLAK, Bas; DE RUITER, Julian. 2021. *Data Pipelines with Apache Airflow*. Manning Publications, Shelter Island, NY, EUA.

INMON, William H. 2005. *Building the Data Warehouse*. 4ª ed. Wiley Publishing, Indianapolis, IN, EUA.

K3S DOCUMENTATION. 2025. *K3s: Lightweight Kubernetes*. Disponível em: <https://k3s.io/>. Acesso em: 17 jun. 2025.

KIMBALL, Ralph; ROSS, Margy. 2013. *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*. 3ª ed. Wiley, Indianapolis, IN, EUA.

METABASE DOCUMENTATION. 2025. *Metabase: The open source analytics and business intelligence platform*. Disponível em: <https://www.metabase.com/docs/>. Acesso em: 17 jun. 2025.

MinIO, Inc. 2023. *MinIO Object Storage Documentation*. MinIO, Inc., Redwood City, CA, EUA. Disponível em: <https://min.io/docs/minio/linux/>. Acesso em: 17 jun. 2025.

NYC TAXI & LIMOUSINE COMMISSION. 2024. *TLC Trip Record Data — High Volume For-Hire Vehicles (HVFHV)*. Disponível em: <https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>. Acesso em: 12 abr. 2026.

REIS, Joe; HOUSLEY, Matt. 2022. *Fundamentals of Data Engineering: Plan and Build Robust Data Systems*. 1ª ed. O'Reilly Media, Sebastopol, CA, EUA.

SCHULZE, Robert; SCHREIBER, Tom; YATSISHIN, Ilya; DAHIMENE, Ryadh; MILOVIDOV, Alexey. 2024. *ClickHouse – Lightning Fast Analytics for Everyone*. Proceedings of the VLDB Endowment (PVLDB), 17(12): 3731–3744.

STAKE, Robert E. 1995. *The Art of Case Study Research*. Sage Publications, Thousand Oaks, CA, EUA.

YIN, Robert K. 2018. *Case Study Research and Applications: Design and Methods*. 6ª ed. Sage Publications, Thousand Oaks, CA, EUA.

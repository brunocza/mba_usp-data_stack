

# Avaliação de metodologias e técnicas para implementação de uma *stack* moderna de dados *open source*

Bruno Czarnescki¹*; Ernane José Xavier Costa²

¹ MBA em Engenharia de Software — USP/Esalq. Discente. Piracicaba, SP, Brasil
² MBA em Engenharia de Software — USP/Esalq. Docente orientador. Piracicaba, SP, Brasil
\*autor correspondente: brunocza1@gmail.com

---

## Resumo

Este trabalho implementou e avaliou quantitativamente uma *stack* de engenharia de dados composta exclusivamente por tecnologias *open source*, em **configuração single-node** sobre *Kubernetes* (K3s) gerenciado via *GitOps* (Argo CD). A *stack* integrou Apache Airflow e Astronomer Cosmos para orquestração, MinIO como *data lake* compatível com S3, ClickHouse como motor analítico colunar, dbt para transformações governadas, Metabase para visualização e Prometheus/Grafana para observabilidade. A avaliação adotou a arquitetura *medallion* (bronze/silver/gold) sobre 232 milhões de registros do programa *High Volume For-Hire Vehicles* da cidade de Nova York, distribuídos em doze arquivos *Parquet* mensais de 2023. Os resultados quantificaram o tempo do pipeline ponta a ponta, as propriedades físicas das camadas materializadas e o ganho da camada gold em duas perguntas de negócio semanticamente equivalentes, com consultas no gold executando em pelo menos três ordens de grandeza menos tempo do que sobre o bronze. A pesquisa incluiu ainda uma validação cruzada em plataforma gerenciada: o mesmo projeto dbt foi reexecutado em um *SQL Warehouse Serverless* 2X-Small do Databricks via troca de *adapter*, e as duas perguntas-chave do *benchmark* foram repetidas com a mesma metodologia. O padrão de aceleração intra-plataforma — isto é, o ganho proporcional ao avançar de bronze para gold — foi preservado em ambos os engines, embora a magnitude absoluta dos tempos no gold tenha diferido em duas a três ordens de grandeza e o custo recorrente estimado tenha diferido em cerca de uma ordem de grandeza. O conjunto dessas evidências oferece base concreta para decisões de arquitetura entre soluções auto-hospedadas e gerenciadas em projetos analíticos de pequeno e médio porte.

**Palavras-chave:** engenharia de dados; *open source*; Kubernetes; dbt; arquitetura *medallion*

---

## Introdução

O cenário contemporâneo da tecnologia da informação é marcado pelo crescimento acelerado no volume, na velocidade e na variedade dos dados produzidos por organizações e dispositivos conectados. Esse cenário traz desafios concretos para empresas que pretendem extrair valor analítico e apoiar suas decisões em evidências. A engenharia de dados surge nesse contexto como disciplina central, dedicada à construção e operação de sistemas robustos para coleta, armazenamento, processamento e disponibilização de dados em escala (Reis e Housley, 2022).

A adoção de uma *stack* moderna baseada em ferramentas *open source* tem sido uma alternativa estratégica relevante. Reis e Housley (2022) descrevem o ciclo de vida da engenharia de dados como uma sequência integrada de geração, ingestão, transformação, armazenamento e servimento de dados, e nesse ciclo as ferramentas abertas trazem três vantagens práticas: flexibilidade arquitetural, ausência de custo de licenciamento e boa integração com o ecossistema *cloud-native*. Essa abordagem é particularmente atrativa para organizações que precisam de controle total sobre a própria infraestrutura, querem evitar dependência de fornecedor e precisam adaptar componentes específicos às suas necessidades de governança.

Apesar do interesse crescente, a literatura ainda apresenta lacunas quanto à integração prática de múltiplas ferramentas em uma *stack* coesa, sobretudo em cenários auto-hospedados sobre orquestradores de contêineres. As decisões de arquitetura — escolha do formato de armazenamento, do motor analítico, do orquestrador e da camada de transformação — envolvem *trade-offs* que são difíceis de quantificar isoladamente. Ainda há dúvidas sobre o ganho real que padrões consolidados como a arquitetura *medallion* (Databricks, 2022) trazem para cargas analíticas reais, quando comparados a abordagens mais simples.

O objetivo deste trabalho foi implementar e avaliar quantitativamente uma *stack* moderna de engenharia de dados composta exclusivamente por componentes *open source*, em **configuração single-node** sobre um cluster Kubernetes leve (K3s), orquestrada via Apache Airflow, com armazenamento em MinIO, processamento analítico em ClickHouse e transformações governadas em dbt. A avaliação abrangeu quatro frentes: o desempenho do pipeline ponta a ponta, as propriedades físicas das camadas materializadas, o ganho mensurável da arquitetura *medallion* em perguntas de negócio sobre 232 milhões de registros e uma análise comparativa com a plataforma gerenciada Databricks. A análise comparativa foi sustentada por uma validação experimental quantitativa: o mesmo projeto dbt foi reexecutado em ambas as plataformas e as duas perguntas-chave do *benchmark* foram repetidas com a mesma metodologia, gerando implicações quantificáveis em custo recorrente e tempo de resposta.

---

## Material e Métodos

Esta é uma pesquisa aplicada, conduzida como um estudo de caso único em ambiente controlado, sobre um cenário realista de engenharia de dados. A escolha pelo estudo de caso permite uma análise aprofundada de um fenômeno contemporâneo em seu contexto real, sobretudo quando os limites entre o fenômeno e seu contexto não são claramente distinguíveis (Yin, 2018). Adota-se abordagem mista: análises qualitativas — sobre integração entre componentes, facilidade de operação no dia a dia, aderência a boas práticas e governança das transformações — e análises quantitativas, focadas em tempo de execução, desempenho de consultas e uso de recursos computacionais (Stake, 1995; Yin, 2018).

Optou-se pelo uso de dados reais públicos do programa *High Volume For-Hire Vehicles* (HVFHV) da *NYC Taxi & Limousine Commission* (NYC Taxi & Limousine Commission, 2024), distribuídos em 12 arquivos *Parquet* mensais correspondentes ao ano de 2023, totalizando aproximadamente 5,5 GB compactados e 232 milhões de registros. A escolha por dados públicos eliminou a necessidade de submissão ao Comitê de Ética em Pesquisa, uma vez que os dados são abertos e anônimos por origem, e fortaleceu a representatividade das medições realizadas. A pesquisa foi conduzida em ambiente próprio do autor, localizado na cidade de Curitiba, Paraná, Brasil.

Para cada etapa do ciclo de dados, foi aplicada uma metodologia compatível com a função desempenhada:

- **Orquestração de pipelines** — A plataforma Apache Airflow (Apache Software Foundation, 2023) foi utilizada para definir, programar e monitorar os fluxos de trabalho como *Directed Acyclic Graphs* [DAGs]. O Airflow é amplamente reconhecido por sua capacidade de gerenciar pipelines complexos, automatizar tarefas e tratar falhas de forma declarativa (Harenslak e De Ruiter, 2021). A integração entre Airflow e dbt foi implementada por meio do *Astronomer Cosmos* (Astronomer, 2025), que expõe cada modelo dbt como uma *task* Airflow nativa, permitindo *retries* individuais e visualização de *lineage* no grafo da DAG.
- **Transformação e governança de dados** — O dbt (dbt Labs, 2023) foi adotado para aplicar práticas de engenharia de software aos pipelines analíticos, viabilizando versionamento, testes automatizados e documentação das transformações SQL. O dbt facilitou a construção de modelos transformados e garantiu a qualidade e a consistência dos dados antes de serem consumidos para análise.
- **Armazenamento de objetos** — Os dados brutos foram armazenados no MinIO (MinIO, Inc., 2023), um sistema de armazenamento de objetos de alto desempenho compatível com a API S3 da AWS e nativo de Kubernetes. Essa compatibilidade garantiu interoperabilidade com as demais ferramentas do ecossistema de dados.
- **Processamento analítico** — O banco colunar ClickHouse (Schulze et al., 2024) foi utilizado como motor *Online Analytical Processing* [OLAP], adequado a consultas analíticas que envolvem agregação e filtragem sobre grandes volumes de dados. O modelo colunar e a execução vetorizada do ClickHouse entregam tempo de resposta na casa dos milissegundos para esse tipo de carga.
- **Visualização e observabilidade** — A plataforma Metabase (Metabase Documentation, 2025) foi prevista para a criação de *dashboards* interativos. A observabilidade da *stack* foi instrumentada com Prometheus e Grafana, totalizando 15 *dashboards* que cobriram o cluster Kubernetes, Airflow, ClickHouse, MinIO e métricas das tabelas analíticas.

**Arquitetura de dados medallion**

A arquitetura *medallion*, também referida como *multi-hop architecture* (Databricks, 2022), organiza os dados em camadas progressivas de refinamento, denominadas bronze, silver e gold. Cada camada cumpre um papel funcional distinto no ciclo de processamento analítico. A camada bronze armazena os dados brutos, ingeridos diretamente das fontes em sua forma original; sua imutabilidade permite o reprocessamento de qualquer etapa subsequente sem retornar ao sistema de origem. A camada silver contém dados tipados, validados e enriquecidos, com a aplicação de regras de qualidade, conversões de tipo, filtragem de registros corrompidos e *joins* com dimensões. A camada gold consolida agregações e métricas de negócio prontas para consumo por *dashboards*, relatórios e modelos analíticos, tipicamente compostas por tabelas pequenas, ordenadas por chaves analíticas e dimensionadas para responder em milissegundos.

A ideia de separar dados em camadas vem da literatura clássica de *data warehousing*. Inmon (2005) propôs a noção de *Corporate Information Factory*, organizando dados em zonas de *staging*, integração e apresentação. Kimball e Ross (2013) consolidaram a modelagem dimensional, distinguindo entre tabelas de fatos brutas e agregadas. A nomenclatura *medallion* foi popularizada pela Databricks (2022) e ganhou ampla adoção em projetos modernos como evolução pragmática desses conceitos para o contexto de *lakehouse*. Reis e Housley (2022) sustentam que essa separação em zonas é parte essencial do ciclo de vida da engenharia de dados: a camada bronze cumpre papel imutável e auditável, a silver expressa o estado limpo e reutilizável dos dados e a gold concentra valor de negócio direto para as áreas consumidoras.

A arquitetura *medallion* foi escolhida nesta pesquisa por quatro razões: (i) separação clara de responsabilidades entre ingestão, limpeza e analítica, o que facilita manutenção e localização de falhas; (ii) reprocessabilidade, já que preservar o bronze imutável permite reconstruir silver e gold sem reingerir dados; (iii) governança e linhagem, com a camada silver concentrando os testes de qualidade do dbt e o *lineage* gerado oferecendo visibilidade ponta a ponta; e (iv) padronização de mercado, o que aumenta a relevância prática do estudo e facilita a comparação com soluções gerenciadas. Cada camada foi materializada como um *schema* distinto no ClickHouse e implementada por modelos SQL versionados no projeto dbt: bronze como cópia 1:1 dos *Parquets* originais, silver como dois modelos de limpeza e enriquecimento e gold como cinco modelos analíticos pré-agregados.

**Ambiente de execução**

Para executar e orquestrar os componentes da *stack* optou-se por um cluster K3s, distribuição leve do Kubernetes, em configuração *single-node* (K3s Documentation, 2025). A configuração foi escolhida tendo em vista a Prova de Conceito acadêmica, com o objetivo de maximizar o *throughput* e minimizar o *operational toil*. Uma instalação *single-node* server já integra todos os componentes essenciais do Kubernetes — *control-plane*, *datastore*, *kubelet* e *containerd* — e está pronta para hospedar cargas de trabalho sem agentes adicionais. A versão v1.32.5+k3s1 acompanha o Kubernetes v1.32.5, garantindo conformidade com a *Cloud Native Computing Foundation* [CNCF]. A arquitetura *single-node* reduziu o *overhead* de virtualização em CPU, memória, rede e disco, eliminou *hops* de rede entre componentes e diminuiu a variação de latência — fator importante para a reprodutibilidade dos resultados quantitativos coletados. Para uma Prova de Conceito acadêmica, a ausência de Alta Disponibilidade [HA] foi compensada por *snapshots* do hipervisor para recuperação de desastres; adicionar mais nós traria complexidade sem benefício real, já que o *host* físico permanece como ponto único de falha.

*Tabela 1 — Especificação do nó utilizado nos experimentos*

| Recurso | Valor |
|---|---|
| CPU | 12 vCPUs |
| Memória | 24 GiB |
| Disco | 200 GiB SSD (*local-path*) |
| Sistema operacional | Ubuntu 22.04 LTS |
| Kubernetes | K3s v1.32.5+k3s1 |
| Hipervisor | Proxmox VE |

Fonte: Resultados originais da pesquisa

*Tabela 1b — Versões dos componentes da stack utilizados no experimento*

| Componente | Versão |
|---|---|
| K3s / Kubernetes | v1.32.5+k3s1 (Kubernetes 1.32.5) |
| Argo CD | v3.3.6 (App-of-Apps) |
| Apache Airflow | 3.1.8 (imagem `bx-airflow:3.1.8-cosmos1.14.0`) |
| Astronomer Cosmos | 1.14.0 |
| dbt-core | 1.11.8 |
| dbt-clickhouse (target ClickHouse) | 1.x compatível com dbt-core 1.11 |
| dbt-databricks (target Databricks) | 1.11.7 |
| ClickHouse | 25.5.2.47 |
| MinIO | RELEASE.2023-06-23T20-26-00Z |
| Prometheus | 2.54.1 |
| Grafana | 11.2.0 |
| Metabase | imagem oficial (deploy via Helm chart) |
| Databricks SQL Serverless | *warehouse* 2X-Small, dbsql_version 2026.10 |

Fonte: Resultados originais da pesquisa

**Gerenciamento de infraestrutura via GitOps**

O Argo CD, ferramenta declarativa de *GitOps* para entrega contínua sobre Kubernetes, foi adotado para implantação e gerenciamento da infraestrutura da *stack* no cluster K3s (Argo CD, 2025). Por meio do Argo CD, os manifestos de *deploy* para Airflow, MinIO e ClickHouse foram versionados em um repositório Git e sincronizados automaticamente com o cluster, garantindo que o estado desejado da infraestrutura fosse mantido e facilitando reprodutibilidade, auditoria e recuperação de desastres. O padrão *App-of-Apps* foi adotado: uma aplicação raiz observa o diretório de manifestos e reconcilia automaticamente todas as aplicações filhas, com *self-heal* habilitado.

<img width="2159" height="1736" alt="image" src="https://github.com/user-attachments/assets/53ceeda9-7adc-4510-9eec-98aefdd64491" />

*Figura 1 — Aplicações do cluster no Argo CD sob o padrão App-of-Apps*

Fonte: Resultados originais da pesquisa

**Pipeline de dados implementado**

O pipeline foi implementado como uma única DAG Airflow nomeada `fhvhv_pipeline`, composta pelas *tasks* `create_schemas`, `ingest_bronze_trips`, `ingest_bronze_zones`, `dbt_transform` e `optimize_tables`, executadas sequencialmente. A *task* `create_schemas` cria os bancos `bronze`, `silver` e `gold` no ClickHouse. A *task* `ingest_bronze_trips` ingere os 12 *Parquets* do MinIO no `bronze.fhvhv_trips`, processando um mês por vez para respeitar o limite de memória do ClickHouse. A *task* `ingest_bronze_zones` carrega o CSV de zonas em `bronze.taxi_zones`. A *task* `dbt_transform`, gerada automaticamente pelo *Astronomer Cosmos*, executa cada modelo dbt como uma *task* Airflow nativa. Por fim, `optimize_tables` aplica `OPTIMIZE TABLE FINAL` em todas as tabelas materializadas, consolidando partes do *MergeTree* e reciclando espaço em disco.

<img width="1940" height="1204" alt="fhvhv_pipeline-graph" src="https://github.com/user-attachments/assets/d32c14c6-b080-44c4-ac21-988a8d006850" />

*Figura 2 — Grafo da DAG fhvhv_pipeline no Airflow com integração dbt via Cosmos*

Fonte: Resultados originais da pesquisa

**Projeto dbt**

O projeto dbt contém dois modelos da camada silver e cinco modelos da camada gold. O modelo `fhvhv_trips_clean` aplica tipagem, filtros de qualidade — descartando corridas com tarifa-base não positiva, milhagem fora do intervalo de zero a 200 e duração fora do intervalo de zero a seis horas — e calcula métricas derivadas como `waiting_minutes`, `trip_minutes`, `total_amount` e `driver_pct_of_fare`. O modelo `fhvhv_trips_enriched` é uma *view* que enriquece o silver limpo com nomes de *borough* e *zone* via *join* com `taxi_zones`. Os modelos gold são `daily_revenue` (receita e volume diário com métricas de mediana e percentil 95 da tarifa), `hourly_demand` (mapa de calor por dia da semana e hora), `borough_pairs` (pares origem-destino por *borough*), `driver_economics` (performance mensal dos motoristas) e `shared_vs_solo` (comparativo entre viagens individuais e compartilhadas).

Cada modelo possui testes de qualidade declarados no arquivo `schema.yml`, com verificações de não-nulidade em colunas críticas e de unicidade em chaves de agregação como `trip_date` e `month`. O arquivo `sources.yml` declara as fontes bronze, permitindo que o dbt rastreie a linhagem desde a origem. O comando `dbt docs generate` produz um *site* interativo com *lineage* gráfico, descrições de modelos e colunas e resultados de testes, publicado no endereço público da pesquisa.

<img width="2136" height="1717" alt="image" src="https://github.com/user-attachments/assets/6bc53606-9acc-4c95-a02e-fe3ff6d4fbeb" />

*Figura 3 — Grafo de linhagem dos modelos dbt (bronze → silver → gold)*

Fonte: Resultados originais da pesquisa

<img width="2145" height="1295" alt="image" src="https://github.com/user-attachments/assets/2b7df7d4-2788-4ab4-b591-f633d96f6f2b" />

*Figura 4 — Execução dos testes dbt com aprovação total das asserções de qualidade*

Fonte: Resultados originais da pesquisa

**Validação cruzada em plataforma gerenciada**

Para complementar a análise da *stack* auto-hospedada com evidência comparativa quantitativa, esta pesquisa adotou um procedimento de validação cruzada em plataforma gerenciada de mercado. A motivação foi a lacuna apontada na introdução: faltam comparações empíricas entre soluções *self-hosted* e *managed* em projetos auto-hospedados de pequeno porte. A plataforma escolhida foi o Databricks, referência de mercado para *engines* OLAP gerenciados sobre *lakehouse* (Schulze et al., 2024). A técnica empregada foi a de *adapter swapping* do dbt: o mesmo projeto analítico (modelos, testes, *sources* e *docs*) foi instanciado em um segundo ambiente, substituindo o *adapter* `dbt-clickhouse` por `dbt-databricks` no `profiles.yml`, com adaptações mínimas de dialeto SQL (`toFloat32(...)` → `CAST(... AS FLOAT)`, `dateDiff('minute', a, b)` → `timestampdiff(MINUTE, a, b)`, `quantile(0.5)(col)` → `percentile_approx(col, 0.5)` e remoção de diretivas específicas do *MergeTree* como `order_by` e `settings`).

O ambiente Databricks utilizado foi um *SQL Warehouse Serverless* tamanho 2X-Small (4 DBU/h) na nuvem AWS, sob a modalidade *Free Edition* da plataforma. Por restrições de cota dessa modalidade, a validação foi executada sobre **um mês de dados** (janeiro de 2023, 18,5 milhões de registros) em vez do ano completo utilizado no ClickHouse. Essa restrição é compatível com o objetivo do procedimento — observar o **padrão de aceleração intra-plataforma** — uma vez que o ganho relativo entre camadas é uma proporção que se mantém ao variar a escala absoluta de dados; a comparação direta dos tempos absolutos entre os dois engines não é o objetivo metodológico desta validação. A medalhão do Databricks foi construída como dois modelos *bronze* materializados como *views* sobre arquivos *Parquet* em um *Unity Catalog Volume*, dois modelos *silver* (sendo um *table* e um *view*) e dois modelos *gold* materializados como tabelas em formato Delta — totalizando seis modelos suficientes para alimentar Q1 e Q2.

A metodologia de medição foi mantida idêntica à usada no ClickHouse: para cada par (camada, pergunta), foram realizadas duas iterações de aquecimento de *cache* (descartadas) e cinco medições efetivas, coletando-se tempo, coeficiente de variação e identificador da consulta. Uma **diferença importante de instrumentação** precisa ser registrada: o ClickHouse reporta `query_duration_ms` *server-pure* (apenas o tempo de processamento dentro do *engine*) via `query_log`, enquanto no Databricks o tempo foi coletado via API REST como *wall-clock* entre o envio do *statement* e o estado `SUCCEEDED` — incluindo, portanto, rede e fila de execução. Esse é o motivo pelo qual a comparação direta dos absolutos *cross-platform* foi explicitamente desencorajada na seção de *Resultados*; o tratamento adequado é a leitura do **padrão de aceleração** dentro de cada plataforma como evidência da arquitetura *medallion*. Os dados brutos das medições estão disponíveis em `tcc/evidencias/databricks_benchmark.json` no repositório do projeto.

**Disponibilização do código-fonte**

Todo o desenvolvimento e os artefatos relacionados ao projeto foram disponibilizados publicamente em repositório Git, em <https://github.com/brunocza/mba_usp-data_stack>, permitindo reproduzir integralmente os resultados apresentados. O repositório contém as DAGs Airflow do pipeline principal e dos *benchmarks*, ambos os projetos dbt (ClickHouse em `dags/dbt_demo/` e Databricks em `dbt_databricks/`), os manifestos Kubernetes e as aplicações Argo CD, além dos documentos do TCC e das evidências coletadas, incluindo o JSON com as medições brutas do Databricks.

---

## Resultados e Discussão

**Desempenho do pipeline ponta a ponta**

A Tabela 2 apresenta o tempo de execução por *task* e o tempo total do pipeline `fhvhv_pipeline`, medido em execuções reais via Airflow durante o período de coleta da pesquisa.

*Tabela 2 — Tempo de execução por task do pipeline fhvhv_pipeline (9 execuções bem-sucedidas)*

| Task | Duração média (s) | Mínimo (s) | Máximo (s) |
|---|---:|---:|---:|
| `create_schemas` | 1,3 | 0,1 | 3,6 |
| `ingest_bronze_trips` | 187 | 162 | 293 |
| `ingest_bronze_zones` | 0,4 | 0,2 | 0,5 |
| `dbt_transform` (Cosmos) | 433 | 380 | 520 |
| `optimize_tables` | 214 | 73 | 258 |
| Total do pipeline | 578 | 90 | 850 |

Fonte: Resultados originais da pesquisa

A maior parcela do tempo de execução concentrou-se na transformação dbt e no `OPTIMIZE FINAL`, etapas em que o ClickHouse precisa percorrer toda a tabela bronze para gerar as camadas silver e gold e consolidar partes do *MergeTree*. A ingestão do bronze, embora processe 232 milhões de registros, beneficia-se da leitura paralela dos *Parquets* e do compactador colunar nativo, mantendo o tempo total em poucos minutos para o volume considerado. O mínimo de 90 segundos do total do pipeline corresponde a uma execução em que apenas as *tasks* de transformação dbt foram reexecutadas sobre o bronze já materializado — caso comum de iteração incremental sem reingestão.

<img width="2151" height="1695" alt="image" src="https://github.com/user-attachments/assets/e9a49c03-bed7-4999-96be-1cb225b1b808" />

*Figura 5 — Execuções da DAG fhvhv_pipeline na interface do Airflow*

A Figura 5 exibe o histórico de execuções da DAG `fhvhv_pipeline`: doze execuções bem-sucedidas (estado *Success*), distribuídas entre execuções manuais (iniciadas pelo usuário) e execuções programadas (iniciadas pelo *timetable* horário), com durações entre seis e quatorze minutos, coerentes com os tempos médios reportados na Tabela 2. Além delas, uma execução em andamento no momento da captura (estado *Running*), iniciada pelo *scheduler* às 20:00 do dia 27 de abril de 2026, mostra que a *stack* continuou em operação depois da coleta dos dados estatísticos. A reprodutibilidade da arquitetura é sustentada pelas execuções verdes consecutivas e pela ausência de estado *failed*; as variações de duração refletem, sobretudo, a diferença entre execuções incrementais (apenas as transformações dbt) e execuções completas (reingestão dos *Parquets*).

Fonte: Resultados originais da pesquisa

**Uso de recursos computacionais**

A análise de recursos computacionais foi conduzida com base nas métricas exportadas pelos *exporters* do Prometheus, observadas em tempo real nos *dashboards* de Grafana. A instrumentação cobriu CPU, memória, E/S de disco e rede dos *namespaces* `warehouse` (ClickHouse) e `orchestrator2` (componentes Airflow), totalizando 15 *dashboards* dedicados aos componentes da *stack* e ao nó K3s hospedeiro.


<img width="2151" height="1735" alt="image" src="https://github.com/user-attachments/assets/ec584ec3-6409-4a22-878f-2f581446f212" />

*Figura 6 — Comportamento do ClickHouse durante uma execução do pipeline observado no Grafana (uso de RAM, duração de consultas, taxa de queries, merges ativos e tamanho das tabelas)*

A Figura 6 mostrou o uso eficiente de recursos durante uma execução do `fhvhv_pipeline`. O *Peak RAM Usage* atingiu cerca de 1,5 GiB, valor bem abaixo do limite de 24 GiB do nó (Tabela 1) — folga que comporta cargas bem maiores. O painel *Peak Query Duration* exibiu picos sincronizados às fases de ingestão e de `OPTIMIZE FINAL` do pipeline. O painel *Parts Merges* mostrou um *merge* ativo em `silver.fhvhv_trips_clean` em aproximadamente 95% de progresso, evidenciando o `OPTIMIZE` em andamento. Por fim, os tamanhos reportados na seção *Table Sizes* — bronze `fhvhv_trips` em 11,85 GiB para 232 milhões de linhas, silver `fhvhv_trips_clean` em 6,87 GiB e gold `daily_revenue` em 19,61 KiB para 365 linhas — são coerentes com os valores apresentados na Tabela 3, confirmando a consistência entre as métricas de instrumentação e a inspeção física das tabelas.

Fonte: Resultados originais da pesquisa

**Métricas das tabelas: compressão e volume**

A Tabela 3 apresenta o tamanho em disco, o tamanho descomprimido e a razão de compressão de cada tabela materializada, obtidos diretamente da tabela de sistema `system.parts` após a execução de `OPTIMIZE FINAL`.

*Tabela 3 — Compressão e volume das tabelas após OPTIMIZE FINAL*

| Camada | Tabela | Linhas | Tamanho em disco | Tamanho descomprimido | Razão de compressão |
|---|---|---:|---:|---:|---:|
| bronze | `fhvhv_trips` | 232.490.020 | 11,85 GiB | 39,26 GiB | 3,31× |
| bronze | `taxi_zones` | 265 | 5,01 KiB | 9,77 KiB | 1,95× |
| silver | `fhvhv_trips_clean` | 232.410.875 | 6,87 GiB | 15,80 GiB | 2,30× |
| gold | `daily_revenue` | 365 | 19,59 KiB | 32,79 KiB | 1,67× |
| gold | `hourly_demand` | 168 | 4,62 KiB | 7,88 KiB | 1,71× |
| gold | `borough_pairs` | 45 | 2,15 KiB | 2,62 KiB | 1,22× |
| gold | `driver_economics` | 12 | 1,06 KiB | 0,76 KiB | — |
| gold | `shared_vs_solo` | 3 | 610 B | 196 B | — |

Fonte: Resultados originais da pesquisa

A razão de compressão moderada, próxima de duas a três vezes, refletiu o uso do codec padrão LZ4 do ClickHouse, que privilegia a velocidade de descompressão sobre a taxa de compressão. Nas tabelas gold mais agregadas, o *overhead* dos metadados das partes do *MergeTree* superou o tamanho dos dados, comportamento esperado para tabelas muito pequenas e por isso a razão de compressão é apresentada como indefinida nos dois últimos casos.

**Valor da arquitetura medallion: bronze, silver e gold**

Para quantificar o valor agregado pela transformação dbt, a DAG `benchmark_medallion_dag` executa duas perguntas de negócio semanticamente equivalentes em cada uma das três camadas e coleta métricas diretamente de `system.query_log` do ClickHouse. Cada consulta é identificada por um `log_comment` único, permitindo correlacionar a execução com o registro do *engine*. A DAG executa duas iterações de aquecimento de *cache*, descartadas, seguidas de cinco medições efetivas por execução. Cada execução completa é tratada como um teste independente e persistida em `benchmark.medallion_results`, identificada por `run_id` e `captured_at`. As perguntas avaliadas foram: Q1 — receita diária do ano de 2023, que no bronze exige a reconstrução da coluna `total_amount` pela soma de sete colunas com conversão para `Float64` e filtragem por janela temporal, no silver lê a tabela já limpa, e no gold lê diretamente `daily_revenue`; e Q2 — top 10 pares origem-destino por *borough* por receita, que no bronze exige dois *joins* com `taxi_zones` e conversões de `LocationID`, no silver lê a *view* enriquecida, e no gold lê `borough_pairs`. As métricas coletadas por iteração foram `query_duration_ms`, `read_rows`, `read_bytes`, `memory_usage` e `result_rows`.

A análise a seguir reúne 54 amostras por camada em cada pergunta, acumuladas ao longo de dez execuções independentes da DAG. Para comparar o desempenho entre camadas adotou-se a métrica de **aceleração relativa** — conhecida na literatura técnica como *speedup* — definida como a razão entre o tempo de execução da camada de referência (bronze) e o tempo de execução da camada avaliada (silver ou gold). Em termos práticos, uma aceleração de 5,4× significa que a consulta na camada avaliada respondeu em um quinto do tempo gasto pela mesma consulta no bronze; uma aceleração de 6.266× significa que respondeu em um seis-mil-duzentos-e-sessenta-e-seis avos do tempo. Essa métrica isola o ganho proporcional da arquitetura *medallion* sem depender de unidades absolutas de tempo, o que a torna comparável entre engines com características distintas de *hardware* e instrumentação.

*Tabela 4 — Q1: receita diária de 2023, médias sobre 54 amostras (10 execuções × 5 iterações)*

| Camada | Tempo médio (ms) | Linhas lidas | Bytes lidos | Memória de pico | Aceleração vs bronze |
|---|---:|---:|---:|---:|---:|
| bronze | 26.315 | 210.963.166 | 14,15 GiB | 44,3 MiB | 1,0× (linha-base) |
| silver | 4.872 | 232.410.875 | 3,03 GiB | 16,7 MiB | 5,4× |
| gold | 4,2 | 365 | 7,13 KiB | 0 B | ≈6.266× ¹ |

Fonte: Resultados originais da pesquisa. ¹ Estimativa conservadora limitada pela resolução do `query_log` do ClickHouse (1 ms); ver discussão a seguir.

*Tabela 5 — Q2: top 10 pares origem-destino por borough, médias sobre 54 amostras (10 execuções × 5 iterações)*

| Camada | Tempo médio (ms) | Linhas lidas | Bytes lidos | Memória de pico | Aceleração vs bronze |
|---|---:|---:|---:|---:|---:|
| bronze | 52.544 | 210.963.696 | 17,68 GiB | 120,9 MiB | 1,0× (linha-base) |
| silver | 31.459 | 232.411.405 | 2,38 GiB | 45,3 MiB | 1,7× |
| gold | 12,4 | 45 | 765 B | 320 B | ≈4.237× ¹ |

Fonte: Resultados originais da pesquisa. ¹ Estimativa conservadora limitada pela resolução do `query_log` do ClickHouse (1 ms); ver discussão a seguir.

O salto de desempenho entre bronze e gold ultrapassou três ordens de grandeza em ambas as perguntas. A diferença é explicada por três fatores complementares: o *scan* do *engine*, em que bronze e silver leram centenas de milhões de linhas enquanto gold acessou tabelas pré-agregadas com poucas centenas ou poucas dezenas de linhas; o volume de I/O, que caiu de 14 a 18 GiB no bronze para menos de 10 KiB no gold; e a ausência de operações por linha no gold, uma vez que agregações, conversões de tipo e *joins* já foram executadas durante a carga. O resultado validou empiricamente a arquitetura *medallion*: a camada gold materializada pelo dbt transformou consultas analíticas da ordem de dezenas de segundos para a ordem de milissegundos, viabilizando *dashboards* interativos e análises ad-hoc sobre o mesmo conjunto de dados bruto. A *task* `report_history` da DAG computa média, desvio-padrão e coeficiente de variação por iteração e também agregados sobre todo o histórico persistido, permitindo avaliar tanto a consistência *intra-run* (dentro de cada execução, geralmente abaixo de 20% nas camadas bronze e silver) quanto a variabilidade *cross-run* (entre execuções, naturalmente mais elevada por incorporar o estado do sistema hospedeiro entre execuções e, na camada gold, a resolução de 1 ms do instrumento de medição).

Há uma ressalva importante de instrumentação na leitura das Tabelas 4 e 5. A camada gold opera próxima ao limite de resolução do `query_duration_ms` reportado pelo `query_log` do ClickHouse (1 ms). Os tempos médios da camada gold (4,2 ms em Q1 e 12,4 ms em Q2) estão a poucas unidades acima desse piso, o que torna a *razão exata* da aceleração sensível à granularidade do instrumento. Os números reportados (≈6.266× em Q1 e ≈4.237× em Q2) devem, portanto, ser lidos como **estimativas conservadoras** indicando ganho **de pelo menos** três ordens de grandeza, sem que a magnitude precisa possa ser inferida com a resolução disponível. A interpretação prática se mantém: a diferença é grande o suficiente para mudar a classe de uso das consultas analíticas (de *batch* para interativo), que é justamente o objetivo da camada gold materializada.

<img width="2134" height="1729" alt="image" src="https://github.com/user-attachments/assets/c9f8c6bb-f0ec-4803-a03b-50966363b17d" />

*Figura 7 — Relatório consolidado do benchmark medallion com aceleração por camada e estatísticas cross-run*

Fonte: Resultados originais da pesquisa

**Validação experimental no Databricks**

A metodologia da validação cruzada em plataforma gerenciada — incluindo critério de seleção da plataforma, princípio de *adapter swapping*, lista de adaptações de dialeto SQL, configuração do *warehouse* e diferenças de instrumentação entre `query_log` (ClickHouse) e wall-clock via API REST (Databricks) — está descrita na seção *Material e Métodos*, subseção *Validação cruzada em plataforma gerenciada*. Esta subseção apresenta os resultados experimentais e sua interpretação.

A construção da medalhão completa pelo `dbt build` na plataforma Databricks levou 68,7 segundos do início ao fim, distribuídos entre as duas *views* de bronze (3,8 s cada), a tabela limpa de silver (46,8 s, etapa mais cara por incluir *cast* dos tipos, filtros de qualidade e escrita em formato Delta), a *view* enriquecida de silver (3,2 s) e as duas tabelas gold (8,6 s para *daily_revenue* e 10,4 s para *borough_pairs*).

*Tabela 6 — Aceleração intra-plataforma da arquitetura medallion: Databricks e ClickHouse lado a lado*

| Pergunta | Camada | Databricks ms (CV%) | Aceleração DBX vs bronze | ClickHouse ms (referência) | Aceleração CH vs bronze |
|---|---|---:|---:|---:|---:|
| Q1 — receita diária | bronze | 6.041 (3,5%) | 1,0× (linha-base) | 26.315 | 1,0× (linha-base) |
| Q1 — receita diária | silver | 1.165 (5,3%) | 5,2× | 4.872 | 5,4× |
| Q1 — receita diária | gold | 1.179 (5,2%) | 5,1× | 4,2 | ≈6.266× ¹ |
| Q2 — top *borough pairs* | bronze | 7.741 (2,3%) | 1,0× (linha-base) | 52.544 | 1,0× (linha-base) |
| Q2 — top *borough pairs* | silver | 3.325 (16,3%) | 2,3× | 31.459 | 1,7× |
| Q2 — top *borough pairs* | gold | 1.089 (1,6%) | 7,1× | 12,4 | ≈4.237× ¹ |

Fonte: Resultados originais da pesquisa. ClickHouse: 54 amostras (10 execuções × 5 iterações) sobre 232 milhões de registros, tempos de `query_log.query_duration_ms` (*server-pure*). Databricks: 5 amostras sobre 18,5 milhões de registros (jan/2023), tempos de *wall-clock* via API REST do *SQL Warehouse Serverless* 2X-Small (4 DBU/h). ¹ Ver caveat sobre limite de resolução do `query_log` na discussão da Tabela 5.

A Tabela 6 organiza o achado central deste estudo: o **padrão de aceleração intra-plataforma é preservado em ambos os engines**. No Databricks, o gold respondeu de 5,1 a 7,1 vezes mais rápido que o bronze; no ClickHouse, o ganho é de duas a três ordens de grandeza. A leitura **direta cruzada** dos absolutos, contudo, é desencorajada por duas razões metodológicas explicitadas na seção *Material e Métodos*: a escala de dados difere por um fator 12 (232 milhões *versus* 18,5 milhões de registros, decorrente de cota da modalidade gratuita do Databricks) e o método de medição não é equivalente (CH usa `query_log` *server-pure*; DBX usa *wall-clock*, que inclui rede e fila de execução). Comparações *cross-platform* devem privilegiar o **padrão de aceleração** intra-plataforma, e não a magnitude bruta de cada célula.

A diferença na magnitude observada entre os dois engines no gold (5-7× no Databricks *versus* milhares de vezes no ClickHouse) é estrutural: o Databricks Serverless 2X-Small mostrou um **piso de aproximadamente um segundo** por consulta, decorrente do custo fixo de inicialização (orquestração, despacho de tarefas, leitura de metadados em armazenamento externo); para volumes pequenos pré-agregados como os do gold (centenas de linhas), esse custo fixo domina o tempo total e impede que a redução de I/O se traduza em redução proporcional de latência. O ClickHouse, por ser embarcado em um único processo e operar sobre tabelas em armazenamento local, evita esse custo e responde em microssegundos no gold. Em termos práticos para o objetivo deste trabalho (*dashboards* interativos e análises ad-hoc), a diferença é perceptível: a *stack* auto-hospedada entrega o gold em tempo de "instantâneo", enquanto a plataforma gerenciada introduz uma latência fixa próxima de um segundo por consulta — preço razoável em cenários de escala variável e sem manutenção operacional, mas que altera a classe de uso para BI ad-hoc.

Para a análise de custos, o experimento consumiu aproximadamente quatro minutos de tempo de computação no Databricks, o que correspondeu a cerca de 0,27 DBU. A preço de tabela público do Databricks SQL Serverless (US$ 0,70 por DBU em ambiente de produção), a execução completa da medalhão e do *benchmark* custou aproximadamente vinte centavos de dólar. Esse valor é negligenciável isoladamente, mas escalando para um cenário de uso contínuo — por exemplo, oito horas por dia de uso analítico ao longo de vinte e dois dias úteis no mês — o mesmo *warehouse* 2X-Small consumiria 704 DBU mensais, equivalentes a aproximadamente quinhentos dólares por mês apenas em computação. Como referência comparável, a *stack* auto-hospedada deste trabalho pode ser executada em uma máquina virtual com especificações semelhantes (8 CPUs, 32 GiB de memória) por um aluguel mensal de aproximadamente trinta a cinquenta dólares em provedores como Hetzner ou Contabo, ou sem custo recorrente quando hospedada em *hardware* próprio já amortizado. A diferença de uma ordem de grandeza no custo recorrente é o *trade-off* mais tangível entre as duas abordagens.

Vale registrar que essa comparação foi intencionalmente concentrada no **custo de computação como primeira ordem**, e não em custo total de propriedade [TCO]. Para a *stack* auto-hospedada, foram omitidos o tempo de administração da infraestrutura (sysadmin, patching, monitoramento ativo), o consumo de energia elétrica (estimado em aproximadamente 100 W em uso, equivalentes a cerca de US$ 5 a US$ 10/mês a tarifas residenciais brasileiras) e a amortização de *hardware* próprio (aproximadamente US$ 55/mês quando se assume um servidor de US$ 2.000 amortizado em 36 meses). Para o Databricks, foram omitidos os custos de armazenamento (S3 do *Unity Catalog*), o egresso de rede e licenças adicionais como *Unity Catalog Premium* para governança avançada. A intenção da comparação é indicar a magnitude esperada para apoiar a decisão de arquitetura; uma análise completa de TCO requer estudo dedicado e está fora do escopo deste trabalho.

<img width="2138" height="1681" alt="image" src="https://github.com/user-attachments/assets/6caca360-3915-4498-8af9-2c14fccd4bc8" />

*Figura 8 — Execução bem-sucedida do projeto dbt como Job nativo do Databricks Workflows*

Fonte: Resultados originais da pesquisa

<img width="2109" height="1360" alt="image" src="https://github.com/user-attachments/assets/66e56fe3-ef23-4e04-8b61-67bb3cc53666" />

*Figura 9 — Grafo de linhagem do projeto dbt no Databricks (bronze → silver → gold)*

Fonte: Resultados originais da pesquisa

A Figura 8 apresenta a execução bem-sucedida do projeto dbt como *Job* nativo do Databricks Workflows, evidenciando que o mesmo repositório versionado foi consumido pelas duas plataformas. A Figura 9 complementa essa evidência com o grafo de linhagem dos seis modelos dbt (bronze → silver → gold) gerado automaticamente pela documentação do dbt sobre o projeto Databricks, idêntico em estrutura ao do projeto ClickHouse. Sintetizando as observações experimentais com as demais dimensões pertinentes à decisão de arquitetura, a Tabela 7 organiza a comparação qualitativa entre a *stack* auto-hospedada deste trabalho e a plataforma Databricks gerenciada.

*Tabela 7 — Análise comparativa qualitativa entre stack open source e plataforma Databricks*

| Dimensão | Stack open source (K3s) | Databricks |
|---|---|---|
| Custo de licenciamento | Zero | Por DBU consumida (US$ 0,70/DBU em produção) |
| Custo de infraestrutura mensal estimado | US$ 30 a 50/mês em VM equivalente; zero em *hardware* próprio | Aproximadamente US$ 500/mês para 8h/dia em *warehouse* 2X-Small (704 DBU) |
| Tempo de *setup* inicial | Da ordem de horas (K3s, Argo CD e Helm) | Da ordem de minutos (*workspace* e *upload*) |
| Tempo de resposta no gold (medalhão) | Microssegundos a milissegundos | Aproximadamente um segundo (custo fixo de inicialização) |
| Monitoramento embutido | Prometheus e Grafana, 15 *dashboards* | *Spark UI* e *Databricks Monitoring* |
| Orquestração | Apache Airflow e *Astronomer Cosmos* | *Databricks Workflows* (validado neste estudo) |
| Governança e linhagem | dbt tests e dbt docs | dbt e *Unity Catalog* |
| Portabilidade entre plataformas | Qualquer cluster Kubernetes | Dependência da plataforma Databricks |
| Controle de infraestrutura | Total, via *GitOps* e infraestrutura própria | Parcial, plataforma gerenciada |
| Escalabilidade | Manual, por adição de nós ao cluster | Automática |
| Reutilização do projeto dbt | Nativa | Validada experimentalmente neste estudo (Tabela 6) |

Fonte: Resultados originais da pesquisa

A comparação mostrou situações em que cada abordagem se sai melhor. A *stack* auto-hospedada em Kubernetes favorece cenários que exigem controle total da infraestrutura, previsibilidade de custos, ausência de dependência de fornecedor e governança auditável via *GitOps*. A plataforma gerenciada favorece cenários que priorizam *time-to-value* reduzido, escalabilidade automática e governança embutida via *Unity Catalog*. A portabilidade do projeto dbt entre as duas configurações, confirmada pela troca de *adapter*, mostra que a plataforma de execução pode ser trocada ao longo do ciclo de vida do produto analítico sem perder o investimento feito em modelagem, testes e documentação. Isso confirma a recomendação de Reis e Housley (2022) por ferramentas desacopladas como princípio de arquitetura de dados moderna.

**Delimitação do escopo experimental**

A avaliação desta pesquisa concentrou-se em quatro frentes, derivadas das lacunas apontadas no ciclo preliminar: indicadores quantitativos do pipeline ponta a ponta (Tabela 2), propriedades físicas das camadas materializadas (Tabela 3), o ganho mensurável da arquitetura *medallion* em duas perguntas de negócio semanticamente equivalentes (Tabelas 4 e 5) e a validação cruzada do mesmo projeto dbt em uma segunda plataforma analítica (Tabela 6). Duas frentes complementares — escalabilidade por volume de dados com estratégias de recarga total *versus* incremental, e comportamento sob carga concorrente com diferentes níveis de *threads* — foram mapeadas no planejamento como trabalho futuro. A arquitetura *medallion* já forma um experimento multicenário com três camadas e duas perguntas, e dá apoio estatístico ao achado principal com mais de dez execuções cumulativas e coeficientes de variação **por iteração (intra-run)** inferiores a 20% nas camadas bronze e silver — o que mostra consistência das medições dentro de cada execução. A variabilidade *cross-run* — agregada sobre todas as execuções — é naturalmente mais elevada, por refletir o estado do sistema hospedeiro entre execuções e, na camada gold, a resolução de 1 ms do `query_log` discutida anteriormente.

**Limitações e ameaças à validade**

Esta seção sistematiza, segundo o quadro de Yin (2018), as principais ameaças à validade dos resultados aqui apresentados, tornando explícitas as condições sob as quais cada achado é defensável.

Quanto à **validade de construto** (a medida captura o que se propõe a captar): no ClickHouse, o tempo de execução foi extraído do `query_duration_ms` do `query_log`, que é uma medida *server-pure* — registra apenas o tempo de processamento dentro do *engine*. No Databricks, o tempo foi coletado em *wall-clock* via API REST, incluindo rede e fila de execução. As duas medições não são, portanto, equivalentes para uma comparação direta de absolutos *cross-platform*; este trabalho privilegia a leitura do **padrão de aceleração intra-plataforma** como evidência da arquitetura *medallion* e tornou explícita essa diferença de instrumentação na nota da Tabela 6.

Quanto à **validade interna** (a relação observada entre causa e efeito é robusta): a camada gold no ClickHouse opera próxima ao limite de resolução do `query_log` (1 ms), o que torna a aceleração absoluta reportada uma estimativa conservadora; o coeficiente de variação **por iteração (intra-run)** inferior a 20% nas camadas bronze e silver e a ausência de correlação entre ordem da execução e tempo medido (mais de dez execuções independentes intercaladas no tempo) reduzem a ameaça de viés de ordem ou de aquecimento residual de *cache*. A variabilidade *cross-run* (agregada entre execuções) é naturalmente mais elevada e reportada na seção de Resultados por meio do *report_history* (Figura 7), refletindo a carga ambiental do sistema hospedeiro e, na camada gold, a granularidade do instrumento de medição.

Quanto à **validade externa** (os resultados generalizam): a configuração *single-node* do ClickHouse não generaliza diretamente para arquiteturas multi-nó com replicação ou *sharding*, em que coordenação e movimentação de dados introduzem fatores ausentes deste estudo; a janela de um mês adotada na validação Databricks limita a inferência sobre o comportamento dessa plataforma em volumes maiores; e o caráter de **estudo de caso único** (Yin, 2018) limita a generalização dos resultados absolutos para outros domínios de dados ou padrões de consulta — replicações em outros *datasets* e cargas estão indicadas como trabalho futuro.

Quanto à **confiabilidade** (o estudo é reprodutível): o repositório Git público versiona todos os manifestos *Kubernetes*, as DAGs Airflow, os dois projetos dbt (ClickHouse e Databricks) e os documentos do TCC; as Tabelas 1 e 1b documentam *hardware* e versões dos componentes; o JSON com cada amostra bruta de tempo do *benchmark* Databricks está em `tcc/evidencias/`; e o histórico cumulativo do *benchmark* ClickHouse é persistido em `benchmark.medallion_results` no próprio *engine*, com `run_id` e `captured_at` por execução.

---

## Conclusão

Os resultados apresentados mostram que é possível construir uma *stack* moderna de engenharia de dados usando apenas tecnologias *open source*, com desempenho comparável ao de soluções comerciais. O K3s em configuração *single-node* funcionou bem para a prova de conceito: manteve o consumo de recursos baixo e a operação simples de acompanhar. O uso do Argo CD para o *deploy* da infraestrutura e para a sincronização automática de manifestos, DAGs e modelos dbt entregou, na prática, os benefícios prometidos pelo *GitOps* — automação, consistência entre o que está no Git e o que está rodando, e reprodutibilidade do ambiente.

A implementação completa do projeto dbt seguindo a arquitetura *medallion* mostrou que a *stack* aguenta cargas de dados reais — na casa das centenas de milhões de registros — com governança, testes automatizados e documentação que evolui junto com o código. A integração com o Airflow via *Astronomer Cosmos* trouxe três ganhos concretos: visibilidade do pipeline ponta a ponta, *retries* no nível do modelo individual (e não da DAG inteira) e *lineage* dos modelos visível diretamente no grafo da DAG.

Os números coletados nos *benchmarks* confirmaram o ganho prático da arquitetura *medallion*: consultas na camada gold rodaram em ordens de grandeza menos tempo do que as mesmas consultas na camada bronze, nas duas perguntas avaliadas. Esse resultado dá apoio empírico à recomendação da literatura por arquiteturas *multi-hop* em *lakehouses* analíticos. A comparação com o Databricks — feita pela reexecução do mesmo projeto dbt e dos mesmos *benchmarks* nas duas plataformas (Tabela 6) — produziu material concreto para a decisão entre soluções auto-hospedadas e gerenciadas: o padrão de aceleração entre camadas se manteve em ambas, mas a magnitude absoluta no gold diferiu em duas a três ordens de grandeza (microssegundos a milissegundos no ClickHouse *versus* cerca de um segundo no Databricks Serverless) e o custo recorrente estimado diferiu em cerca de uma ordem de grandeza. Na prática, a escolha entre as duas depende do que pesa mais para cada caso: rapidez de entrada em operação (*time-to-value* favorece o gerenciado) ou custo previsível com tempo de resposta interativo (favorece o auto-hospedado).

Cabe registrar, em caráter de reflexão crítica, que o próprio formato de **estudo de caso aplicado** envolve um compromisso entre profundidade e amplitude: ao optar por mergulhar em uma trajetória específica — uma *stack*, um *dataset*, duas perguntas analíticas representativas — em vez de buscar generalização ampla, este trabalho documenta o que se mostrou robusto sob restrições reais (recursos limitados, edição gratuita da plataforma gerenciada, janela mensal de dados na validação cruzada), sem pretender ser uma conclusão definitiva sobre arquiteturas em geral. A **execução em duas plataformas distintas** tornou visível algo que estudos com um único motor tendem a esconder: a aceleração observada entre as camadas da arquitetura *medallion* não é uma propriedade do padrão arquitetural sozinho — ela vem da combinação entre o **padrão de modelagem**, o **motor de execução** e o **formato das consultas** escolhidas. Por isso, separar esses três fatores em medições futuras tende a render mais aprendizado do que simplesmente aumentar o volume de dados ou o número de perguntas sobre um único motor. Outro ponto que merece destaque é que a própria escolha de *como medir tempo* — `query_duration_ms` *versus wall-clock* — já é uma decisão sobre o que se considera importante (o custo no servidor ou o tempo total percebido pelo usuário final), o que justifica privilegiar comparações dentro de uma mesma plataforma como evidência principal e tratar comparações entre plataformas como indicações qualitativas. Essa **postura metodológica explícita** — reconhecer o que cada medida permite ou não afirmar, e quais premissas cada ferramenta traz consigo — é, mais do que qualquer número específico apresentado, a parte deste trabalho que mais facilmente se aplica a futuros projetos de comparação entre arquiteturas de dados.

Como **trabalho futuro**, este estudo abre quatro frentes de extensão direta: (i) replicar a configuração em ClickHouse multi-nó e medir os custos de coordenação que o *sharding* nativo introduz, contrastando-os com o ganho de paralelismo; (ii) avaliar pipelines em modo *streaming* ou *Change Data Capture* via *Materialized Views* ou *ClickHouse Kafka engine*, para casos de uso *near real-time*; (iii) integrar governança e linhagem *cross-platform* através de catálogos ativos como *DataHub* ou *OpenMetadata*, complementando o *lineage* embutido do dbt com metadados de fontes externas; e (iv) repetir o mesmo *benchmark medallion* sobre outros domínios de dados (logs de aplicação, séries temporais industriais) para verificar se os resultados aqui apresentados se generalizam para padrões de consulta diferentes.

O conjunto destes elementos — infraestrutura *cloud-native* leve, gestão por *GitOps*, orquestração robusta, armazenamento S3-compatível, processamento analítico de alto desempenho e transformações dbt governadas — resultou em uma arquitetura pronta para uso em projetos reais de engenharia de dados de pequeno e médio porte, cumprindo o objetivo central deste trabalho.

---

## Referências

Apache Software Foundation. 2023. *Apache Airflow Documentation* (v2.5). Apache Software Foundation, Wilmington, DE, EUA. Disponível em: <https://airflow.apache.org/docs/apache-airflow/stable/>. Acesso em: 17 jun. 2025.

Argo CD. 2025. *Argo CD Documentation*. Disponível em: <https://argo-cd.readthedocs.io/en/stable/>. Acesso em: 17 jun. 2025.

Astronomer. 2025. *Astronomer Cosmos: Run dbt projects as Airflow DAGs*. Disponível em: <https://astronomer.github.io/astronomer-cosmos/>. Acesso em: 12 abr. 2026.

Databricks. 2022. *What is the medallion lakehouse architecture?*. Disponível em: <https://www.databricks.com/glossary/medallion-architecture>. Acesso em: 12 abr. 2026.

dbt Labs. 2023. *dbt Documentation: What is dbt?*. dbt Labs, Philadelphia, PA, EUA. Disponível em: <https://docs.getdbt.com/docs/introduction>. Acesso em: 17 jun. 2025.

Harenslak, B.; De Ruiter, J. 2021. *Data Pipelines with Apache Airflow*. Manning Publications, Shelter Island, NY, EUA.

Inmon, W.H. 2005. *Building the Data Warehouse*. 4ed. Wiley Publishing, Indianapolis, IN, EUA.

K3s Documentation. 2025. *K3s: Lightweight Kubernetes*. Disponível em: <https://k3s.io/>. Acesso em: 17 jun. 2025.

Kimball, R.; Ross, M. 2013. *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling*. 3ed. Wiley, Indianapolis, IN, EUA.

Metabase Documentation. 2025. *Metabase: The open source analytics and business intelligence platform*. Disponível em: <https://www.metabase.com/docs/>. Acesso em: 17 jun. 2025.

MinIO, Inc. 2023. *MinIO Object Storage Documentation*. MinIO, Inc., Redwood City, CA, EUA. Disponível em: <https://min.io/docs/minio/linux/>. Acesso em: 17 jun. 2025.

NYC Taxi & Limousine Commission. 2024. *TLC Trip Record Data — High Volume For-Hire Vehicles*. Disponível em: <https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>. Acesso em: 12 abr. 2026.

Reis, J.; Housley, M. 2022. *Fundamentals of Data Engineering: Plan and Build Robust Data Systems*. 1ed. O'Reilly Media, Sebastopol, CA, EUA.

Schulze, R.; Schreiber, T.; Yatsishin, I.; Dahimene, R.; Milovidov, A. 2024. ClickHouse — lightning fast analytics for everyone. *Proceedings of the VLDB Endowment* 17(12): 3731-3744.

Stake, R.E. 1995. *The Art of Case Study Research*. Sage Publications, Thousand Oaks, CA, EUA.

Yin, R.K. 2018. *Case Study Research and Applications: Design and Methods*. 6ed. Sage Publications, Thousand Oaks, CA, EUA.

<!--
═══════════════════════════════════════════════════════════════════════════════
TCC FINAL — Bruno Czarnescki — MBA USP/Esalq
═══════════════════════════════════════════════════════════════════════════════
Versão estruturada conforme Template TCC_PT.docx (USP/Esalq).
Estrutura obrigatória (ordem fixa, sem numeração nos títulos):
  Resumo → Introdução → Material e Métodos → Resultados e Discussão →
  Conclusão → Referências
Limite: 30 páginas (Arial 11, 1,5 espaço, margens 2,5 cm).

Notas para conversão MANUAL para .docx no template oficial USP:
- Substituir HEADER abaixo pelo cabeçalho do template (logo MBA + nome do curso).
- Subtópicos marcados com `**Negrito**` neste markdown devem virar parágrafos
  com a primeira linha recuada 1,25 cm e em negrito (não usar nível ###).
- Tabelas: título ACIMA, fonte ABAIXO, fonte Arial 11, espaçamento simples,
  sem cores, sem negrito interno, sem bordas decorativas.
- Figuras: título e fonte ABAIXO da imagem, fonte Arial 11.
- Itálico em termos estrangeiros (exceto latim, que vai em itálico também).
- Os blocos `<!-- FIGURA N — INSERIR IMAGEM AQUI ... -->` indicam o local
  exato onde inserir cada captura de tela no .docx, com o alvo do print
  descrito dentro do próprio comentário. Remover o bloco HTML após inserir
  a imagem correspondente.
═══════════════════════════════════════════════════════════════════════════════
-->

# Avaliação de metodologias e técnicas para implementação de uma stack moderna de dados open source

Bruno Czarnescki¹*; Ernane José Xavier Costa²

¹ MBA em Engenharia de Software — USP/Esalq. Discente. Piracicaba, SP, Brasil
² MBA em Engenharia de Software — USP/Esalq. Docente orientador. Piracicaba, SP, Brasil
\*autor correspondente: brunocza@gmail.com

---

## Resumo

Este trabalho apresentou a implementação e avaliação de uma stack moderna de engenharia de dados baseada exclusivamente em tecnologias *open source*, executada em ambiente *Kubernetes* (K3s) gerenciado via *GitOps* (Argo CD). A stack integrou Apache Airflow para orquestração, MinIO como *data lake* compatível com S3, ClickHouse como motor analítico colunar, dbt para transformações governadas e Grafana/Prometheus para observabilidade. A avaliação adotou a arquitetura *medallion* (bronze/silver/gold) e utilizou dados reais do programa *High Volume For-Hire Vehicles* da cidade de Nova York, totalizando aproximadamente 232 milhões de registros distribuídos em 12 arquivos *Parquet*. Os resultados demonstraram a viabilidade técnica e o desempenho competitivo da abordagem *open source*, apresentando indicadores quantitativos de tempo de execução do pipeline ponta a ponta, propriedades físicas das camadas materializadas e o ganho mensurável da arquitetura *medallion* em duas perguntas de negócio semanticamente equivalentes, com consultas na camada gold executando em ordens de grandeza menos tempo que sobre a camada bronze. Uma análise comparativa qualitativa com a plataforma gerenciada Databricks evidenciou os *trade-offs* entre custo, complexidade operacional, portabilidade e governança, com a portabilidade do projeto dbt validada pela troca de *adapter* entre as duas plataformas.

**Palavras-chave:** engenharia de dados; *open source*; Kubernetes; dbt; arquitetura *medallion*

---

## Introdução

O cenário contemporâneo da tecnologia da informação é caracterizado pelo crescimento acelerado no volume, na velocidade e na variedade dos dados produzidos por organizações e dispositivos conectados. Esse fenômeno impõe desafios significativos para empresas que pretendem extrair valor analítico e suportar a tomada de decisão baseada em evidências. A engenharia de dados emerge nesse contexto como disciplina central, dedicada à concepção e operação de sistemas robustos para coleta, armazenamento, processamento e disponibilização de dados em escala (Reis e Housley, 2022).

A adoção de uma stack moderna baseada em ferramentas *open source* tem sido uma alternativa estratégica relevante. Reis e Housley (2022) descrevem o ciclo de vida da engenharia de dados como uma sequência integrada de geração, ingestão, transformação, armazenamento e servimento de dados, na qual ferramentas abertas oferecem flexibilidade arquitetural, ausência de custos de licenciamento e ampla integração com ecossistemas estabelecidos. Essa abordagem é particularmente atrativa para organizações que precisam controlar a totalidade de sua infraestrutura, evitar dependência de fornecedor e adaptar componentes específicos às suas necessidades de governança.

Apesar do interesse crescente, a literatura ainda apresenta lacunas quanto à integração prática de múltiplas ferramentas em uma stack coesa, especialmente em cenários auto-hospedados sobre orquestradores de contêineres. As decisões de arquitetura — escolha do formato de armazenamento, do motor analítico, do orquestrador e da camada de transformação — envolvem *trade-offs* que dificilmente são quantificados de forma isolada. Persistem ainda dúvidas sobre o ganho real que padrões consolidados como a arquitetura *medallion* (Databricks, 2022) trazem para cargas analíticas reais quando comparados a abordagens mais simples.

O objetivo deste trabalho foi implementar e avaliar quantitativamente uma stack moderna de engenharia de dados composta exclusivamente por componentes *open source*, executada sobre um cluster Kubernetes leve (K3s), orquestrada via Apache Airflow, com armazenamento em MinIO, processamento analítico em ClickHouse e transformações governadas em dbt. A avaliação abrangeu o desempenho do pipeline ponta a ponta, as propriedades físicas das camadas materializadas, o ganho mensurável da arquitetura *medallion* em perguntas de negócio sobre 232 milhões de registros, e uma análise comparativa qualitativa com a plataforma gerenciada Databricks complementada pela validação da portabilidade do projeto dbt entre as duas plataformas.

---

## Material e Métodos

A pesquisa possui caráter aplicado e foi conduzida como um estudo de caso único em ambiente controlado, com simulação de um cenário realista de engenharia de dados. A escolha pelo estudo de caso permite uma análise aprofundada de um fenômeno contemporâneo em seu contexto real, especialmente quando os limites entre o fenômeno e seu contexto não são claramente evidentes (Yin, 2018). A abordagem é mista, combinando análises qualitativas — sobre integração, facilidade de uso, aderência às boas práticas e governança — e análises quantitativas, focadas em tempo de execução, desempenho de consultas e uso de recursos computacionais (Stake, 1995; Yin, 2018).

Optou-se pelo uso de dados reais públicos do programa *High Volume For-Hire Vehicles* (HVFHV) da *NYC Taxi & Limousine Commission* (NYC Taxi & Limousine Commission, 2024), distribuídos em 12 arquivos *Parquet* mensais correspondentes ao ano de 2023, totalizando aproximadamente 5,5 GB compactados e 232 milhões de registros. A escolha por dados públicos eliminou a necessidade de submissão ao Comitê de Ética em Pesquisa, uma vez que os dados são abertos e anônimos por origem, e fortaleceu a representatividade das medições realizadas. A pesquisa foi conduzida em ambiente próprio do autor, localizado na cidade de Curitiba, Paraná, Brasil.

Para cada etapa do ciclo de dados, foi aplicada uma metodologia compatível com a função desempenhada:

- **Orquestração de pipelines** — A plataforma Apache Airflow (Apache Software Foundation, 2023) foi utilizada para definir, programar e monitorar os fluxos de trabalho como *Directed Acyclic Graphs* [DAGs]. O Airflow é amplamente reconhecido por sua capacidade de gerenciar pipelines complexos, automatizar tarefas e tratar falhas de forma declarativa (Harenslak e De Ruiter, 2021). A integração entre Airflow e dbt foi implementada por meio do *Astronomer Cosmos* (Astronomer, 2025), que expõe cada modelo dbt como uma *task* Airflow nativa, permitindo *retries* individuais e visualização de *lineage* no grafo da DAG.
- **Transformação e governança de dados** — O dbt (dbt Labs, 2023) foi adotado para aplicar práticas de engenharia de software aos pipelines analíticos, viabilizando versionamento, testes automatizados e documentação das transformações SQL. O dbt facilitou a construção de modelos transformados e garantiu a qualidade e a consistência dos dados antes de serem consumidos para análise.
- **Armazenamento de objetos** — Os dados brutos foram armazenados no MinIO (MinIO, Inc., 2023), um sistema de armazenamento de objetos de alto desempenho compatível com a API S3 da AWS, nativo de Kubernetes. Sua compatibilidade com a API S3 garantiu interoperabilidade com diversas ferramentas do ecossistema de dados.
- **Processamento analítico** — O banco colunar ClickHouse (Schulze et al., 2024) foi utilizado como motor *Online Analytical Processing* [OLAP], devido à sua capacidade de executar consultas em tempo real sobre volumes massivos de dados. O ClickHouse é otimizado para cargas analíticas, oferecendo desempenho elevado em cenários que exigem agregação e filtragem rápidas sobre grandes conjuntos de dados.
- **Visualização e observabilidade** — A plataforma Metabase (Metabase Documentation, 2025) foi prevista para a criação de *dashboards* interativos. A observabilidade da stack foi instrumentada com Prometheus e Grafana, totalizando 15 *dashboards* que cobriram o cluster Kubernetes, Airflow, ClickHouse, MinIO e métricas das tabelas analíticas.

**Arquitetura de dados medallion**

A arquitetura *medallion*, também referida como *multi-hop architecture* (Databricks, 2022), organiza os dados em camadas progressivas de refinamento, denominadas bronze, silver e gold. Cada camada cumpre um papel funcional distinto no ciclo de processamento analítico. A camada bronze armazena os dados brutos, ingeridos diretamente das fontes em sua forma original; sua imutabilidade permite o reprocessamento de qualquer etapa subsequente sem retornar ao sistema de origem. A camada silver contém dados tipados, validados e enriquecidos, com a aplicação de regras de qualidade, conversões de tipo, filtragem de registros corrompidos e *joins* com dimensões. A camada gold consolida agregações e métricas de negócio prontas para consumo por *dashboards*, relatórios e modelos analíticos, tipicamente compostas por tabelas pequenas, ordenadas por chaves analíticas e dimensionadas para responder em milissegundos.

A separação em camadas tem raízes na literatura clássica de *data warehousing*. Inmon (2005) propôs a noção de *Corporate Information Factory* organizando dados em zonas de *staging*, integração e apresentação, enquanto Kimball e Ross (2013) consolidaram a modelagem dimensional, distinguindo entre tabelas de fatos brutas e agregadas. A nomenclatura *medallion* foi popularizada pela Databricks (2022) e adotada amplamente em projetos modernos como uma evolução pragmática desses conceitos para o contexto de *lakehouse*. Reis e Housley (2022) sustentam que a separação em zonas é parte essencial do ciclo de vida da engenharia de dados, na qual a camada bronze cumpre papel imutável e auditável, a silver expressa o estado limpo e reutilizável dos dados, e a gold concentra valor de negócio direto para as áreas consumidoras.

A escolha da arquitetura *medallion* para esta pesquisa foi motivada por quatro razões: (i) separação clara de responsabilidades entre ingestão, limpeza e analítica, facilitando manutenção e atribuição de falhas; (ii) reprocessabilidade, uma vez que a preservação do bronze imutável permite reconstruir silver e gold sem reingerir dados; (iii) governança e linhagem, com a camada silver concentrando os testes de qualidade do dbt e o *lineage* gerado oferecendo visibilidade ponta a ponta; e (iv) padronização de mercado, o que aumenta a relevância prática do estudo e facilita a comparabilidade com soluções gerenciadas. Cada camada foi materializada como um *schema* distinto no ClickHouse e implementada por modelos SQL versionados no projeto dbt: bronze como cópia 1:1 dos *Parquets* originais, silver como dois modelos de limpeza e enriquecimento, e gold como cinco modelos analíticos pré-agregados.

**Ambiente de execução**

Para a execução e orquestração dos componentes da stack optou-se pela utilização de um cluster K3s, distribuição leve do Kubernetes, em configuração *single-node* (K3s Documentation, 2025). A escolha foi estratégica para a Prova de Conceito acadêmica, visando maximizar o *throughput* e minimizar o *operational toil*. Uma instalação *single-node* server já integra todos os componentes essenciais do Kubernetes — *control-plane*, *datastore*, *kubelet* e *containerd* — estando pronta para hospedar cargas de trabalho sem agentes adicionais. A versão v1.33.1+k3s1 acompanha o Kubernetes v1.33.1, assegurando conformidade com a *Cloud Native Computing Foundation* [CNCF]. A arquitetura *single-node* minimizou o *overhead* de virtualização em CPU, memória, rede e disco, eliminou *hops* de rede entre componentes e reduziu a variação de latência, fator importante para a reprodutibilidade dos resultados quantitativos coletados. Para uma Prova de Conceito acadêmica, a ausência de Alta Disponibilidade [HA] foi compensada por *snapshots* do hipervisor para recuperação de desastres, e a adição de mais nós acrescentaria complexidade sem benefício real, dado que o *host* físico permanece como ponto único de falha.

*Tabela 1 — Especificação do nó utilizado nos experimentos*

| Recurso | Valor |
|---|---|
| CPU | 12 vCPUs |
| Memória | 24 GiB |
| Disco | 200 GiB SSD (local-path) |
| Sistema operacional | Ubuntu 22.04 LTS |
| Kubernetes | K3s v1.33.1 |
| Hipervisor | Proxmox VE |

Fonte: Dados originais da pesquisa

**Gerenciamento de infraestrutura via GitOps**

O Argo CD, ferramenta declarativa de *GitOps* para entrega contínua sobre Kubernetes, foi adotado para implantação e gerenciamento da infraestrutura da stack no cluster K3s (Argo CD, 2025). Por meio do Argo CD, os manifestos de *deploy* para Airflow, MinIO e ClickHouse foram versionados em um repositório Git e sincronizados automaticamente com o cluster, garantindo que o estado desejado da infraestrutura fosse mantido e facilitando reprodutibilidade, auditoria e recuperação de desastres. O padrão *App-of-Apps* foi adotado: uma aplicação raiz observa o diretório de manifestos e reconcilia automaticamente todas as aplicações filhas, com *self-heal* habilitado.

<!-- FIGURA 1 — INSERIR IMAGEM AQUI
Captura: tela de Applications do Argo CD mostrando o conjunto de aplicações gerenciadas pelo padrão App-of-Apps — root-app, airflow10, clickhouse, grafana, metabase, minio-operator, minio-tenant, prometheus — todas com status Healthy.
Onde capturar: Argo CD UI (https://argocd.bxdatalab.com ou equivalente) > Applications > modo de visualização em grade (Tiles) ou lista, após "Refresh All".
O que destacar: todas as aplicações com indicador de saúde verde (Healthy). Ideal capturar após um Sync bem-sucedido da root-app para mostrar também o status Synced; se estiver Unknown, pode ser deixado assim com justificativa no próprio texto (o importante é o Healthy).
Formato: PNG, tela cheia ou recorte limpo do painel de Applications. -->

*Figura 1 — Aplicações do cluster no Argo CD sob o padrão App-of-Apps*

**(DESCRITIVO — APAGAR APÓS INSERIR IMAGEM: captura da aba Applications do Argo CD mostrando as oito aplicações — root-app, airflow10, clickhouse, grafana, metabase, minio-operator, minio-tenant e prometheus — todas com o indicador de saúde verde (Healthy) e status Synced, visualizadas em modo grade ou lista após "Refresh All".)**

Fonte: Resultados originais da pesquisa

**Pipeline de dados implementado**

O pipeline foi implementado como uma única DAG Airflow nomeada `fhvhv_pipeline`, composta pelas *tasks* `create_schemas`, `ingest_bronze_trips`, `ingest_bronze_zones`, `dbt_transform` e `optimize_tables`, executadas sequencialmente. A *task* `create_schemas` cria os bancos `bronze`, `silver` e `gold` no ClickHouse. A *task* `ingest_bronze_trips` ingere os 12 *Parquets* do MinIO no `bronze.fhvhv_trips`, processando um mês por vez para respeitar o limite de memória do ClickHouse. A *task* `ingest_bronze_zones` carrega o CSV de zonas em `bronze.taxi_zones`. A *task* `dbt_transform`, gerada automaticamente pelo *Astronomer Cosmos*, executa cada modelo dbt como uma *task* Airflow nativa. Por fim, `optimize_tables` aplica `OPTIMIZE TABLE FINAL` em todas as tabelas materializadas, consolidando partes do *MergeTree* e reciclando espaço em disco.

<!-- FIGURA 2 — INSERIR IMAGEM AQUI
Captura: grafo da DAG `fhvhv_pipeline` no Airflow UI, mostrando o encadeamento das tasks: create_schemas → [ingest_bronze_trips, ingest_bronze_zones] → dbt_transform (grupo expandido com os modelos silver e gold do Cosmos) → optimize_tables.
Onde capturar: Airflow UI > DAGs > fhvhv_pipeline > aba "Graph" em uma execução recente de sucesso. Se o grupo `dbt_transform` vier colapsado, clicar para expandir e mostrar os nós dos modelos dbt.
O que destacar: a integração nativa entre Airflow e dbt via Cosmos — cada modelo dbt aparece como uma task Airflow, com pares `.run` e `.test` por modelo. Evidencia a governança ponta a ponta e a rastreabilidade visual do pipeline.
Formato: PNG horizontal, recorte ajustado ao grafo (sem a barra lateral). -->

*Figura 2 — Grafo da DAG fhvhv_pipeline no Airflow com integração dbt via Cosmos*

**(DESCRITIVO — APAGAR APÓS INSERIR IMAGEM: grafo visual da DAG `fhvhv_pipeline` no Airflow UI em uma execução recente de sucesso, mostrando o encadeamento create_schemas → ingest_bronze_trips e ingest_bronze_zones em paralelo → grupo dbt_transform expandido com os nós `.run` e `.test` dos modelos silver e gold do Cosmos → optimize_tables, todos com borda verde de success.)**

Fonte: Resultados originais da pesquisa

**Projeto dbt**

O projeto dbt contém dois modelos da camada silver e cinco modelos da camada gold. O modelo `fhvhv_trips_clean` aplica tipagem, filtros de qualidade — descartando corridas com tarifa-base não positiva, milhagem fora do intervalo de zero a 200 e duração fora do intervalo de zero a seis horas — e calcula métricas derivadas como `waiting_minutes`, `trip_minutes`, `total_amount` e `driver_pct_of_fare`. O modelo `fhvhv_trips_enriched` é uma *view* que enriquece o silver limpo com nomes de *borough* e *zone* via *join* com `taxi_zones`. Os modelos gold são `daily_revenue` (receita e volume diário com métricas de mediana e percentil 95 da tarifa), `hourly_demand` (mapa de calor por dia da semana e hora), `borough_pairs` (pares origem-destino por *borough*), `driver_economics` (performance mensal dos motoristas) e `shared_vs_solo` (comparativo entre viagens individuais e compartilhadas).

Cada modelo possui testes de qualidade declarados no arquivo `schema.yml`, com verificações de não-nulidade em colunas críticas e de unicidade em chaves de agregação como `trip_date` e `month`. O arquivo `sources.yml` declara as fontes bronze, permitindo que o dbt rastreie a linhagem desde a origem. O comando `dbt docs generate` produz um *site* interativo com lineage gráfico, descrições de modelos e colunas e resultados de testes, publicado no endereço público da pesquisa.

<!-- FIGURA 3 — INSERIR IMAGEM AQUI
Captura: grafo de linhagem (lineage) gerado pelo `dbt docs generate`, mostrando o fluxo bronze.fhvhv_trips → silver.fhvhv_trips_clean → silver.fhvhv_trips_enriched → (5 modelos gold), com setas de dependência.
Onde capturar: navegador em `https://dbt-docs.bxdatalab.com/#!/overview` (ou endereço local do dbt docs do projeto) > botão "View Lineage Graph" no canto inferior direito.
O que destacar: os dois níveis de transformação (silver e gold) e as dependências cruzadas via taxi_zones. Evidencia a governança e a rastreabilidade declarativa do projeto dbt.
Formato: PNG, cores padrão do dbt docs, proporção retangular horizontal. -->

*Figura 3 — Grafo de linhagem dos modelos dbt (bronze → silver → gold)*

**(DESCRITIVO — APAGAR APÓS INSERIR IMAGEM: grafo de lineage gerado pelo `dbt docs generate`, mostrando o fluxo bronze.fhvhv_trips e bronze.taxi_zones → silver.fhvhv_trips_clean → silver.fhvhv_trips_enriched → cinco nós gold (daily_revenue, hourly_demand, borough_pairs, driver_economics, shared_vs_solo) com setas de dependência e cores padrão do dbt docs.)**

Fonte: Resultados originais da pesquisa

<!-- FIGURA 4 — INSERIR IMAGEM AQUI
Captura: saída do comando `dbt test` mostrando todas as asserções aprovadas (not_null, unique, relationships), preferencialmente pelos logs da task dbt_test do Airflow ou por terminal com a execução local do dbt.
Onde capturar: (a) Airflow UI > DAGs > fhvhv_pipeline > task `dbt_test` > Logs, ou (b) terminal rodando `dbt test --project-dir dbt/` com todos PASS em verde.
O que destacar: o bloco final com "Done. PASS=N ERROR=0 FAIL=0 ...". Prova que os modelos silver e gold passam nos testes de qualidade declarados no schema.yml.
Formato: PNG do texto do log, recorte focado no bloco de sumário dos testes. -->

*Figura 4 — Execução dos testes dbt com aprovação total das asserções de qualidade*

**(DESCRITIVO — APAGAR APÓS INSERIR IMAGEM: bloco de saída textual do comando `dbt test` ao final da execução, mostrando as linhas de cada asserção `PASS`, seguidas do sumário final no formato "Done. PASS=N WARN=0 ERROR=0 SKIP=0 TOTAL=N", comprovando que todos os testes de qualidade declarados no `schema.yml` dos modelos silver e gold foram aprovados.)**

Fonte: Resultados originais da pesquisa

**Disponibilização do código-fonte**

Todo o desenvolvimento e os artefatos relacionados ao projeto foram disponibilizados publicamente em repositório Git, permitindo a reprodução integral dos resultados apresentados. O repositório contém as DAGs Airflow do pipeline principal e dos *benchmarks*, o projeto dbt completo, os manifestos Kubernetes e as aplicações Argo CD, além dos próprios documentos do TCC e das evidências coletadas.

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

<!-- FIGURA 5 — INSERIR IMAGEM AQUI
Captura: tela de "DAG Runs" do Airflow UI para a DAG `fhvhv_pipeline`.
Onde capturar: Airflow UI > DAGs > fhvhv_pipeline > aba "Runs" (ou "Grid"), filtrar por state=success.
O que destacar: pelo menos 9 execuções todas com status verde (success), mostrando coluna de duração e timestamps. Evidencia a reprodutibilidade e a base estatística das médias apresentadas na Tabela 2.
Formato: PNG, largura mínima 900 px, sem anotações sobre a imagem (USP exige gráfico limpo). -->

*Figura 5 — Execuções bem-sucedidas da DAG fhvhv_pipeline na interface do Airflow*

**(DESCRITIVO — APAGAR APÓS INSERIR IMAGEM: lista ou grade de "DAG Runs" do Airflow UI para a DAG `fhvhv_pipeline`, exibindo ao menos nove execuções com o estado success em verde, com colunas visíveis de run_id, start_date e duration, evidenciando a reprodutibilidade e a base estatística das médias apresentadas na Tabela 2.)**

Fonte: Resultados originais da pesquisa

**Uso de recursos computacionais**

A análise de recursos computacionais foi conduzida com base nas métricas exportadas pelos *exporters* do Prometheus, observadas em tempo real nos *dashboards* de Grafana. A instrumentação cobriu CPU, memória, E/S de disco e rede dos *namespaces* `warehouse` (ClickHouse) e `orchestrator2` (componentes Airflow), totalizando 15 *dashboards* dedicados aos componentes da stack e ao nó K3s hospedeiro.

<!-- FIGURA 6 — INSERIR IMAGEM AQUI
Captura: painel do Grafana mostrando CPU usage e memory working set do pod `clickhouse-shard0-0` do namespace `warehouse` durante uma execução completa da DAG `fhvhv_pipeline` — ou, em alternativa, o dashboard consolidado do cluster durante o intervalo da execução.
Onde capturar: Grafana (ex.: grafana.bxdatalab.com) > dashboards > escolher o painel de ClickHouse ou Node Exporter > ajustar intervalo para uma janela de ~15 min cobrindo uma execução recente do fhvhv_pipeline (ver os start_date/end_date do Airflow para alinhar a janela).
O que destacar: (a) pico de CPU durante a etapa de ingestão e durante o OPTIMIZE FINAL; (b) patamar de memória estável em poucos GiB, bem abaixo do limite de 24 GiB do nó; (c) duração do intervalo marcado coincidente com o tempo médio da Tabela 2. Evidencia o uso eficiente de recursos e a ausência de saturação.
Formato: PNG do painel, fundo escuro padrão do Grafana ou claro — ambos aceitos. -->

*Figura 6 — Utilização de CPU e memória do ClickHouse durante uma execução do pipeline, observada no Grafana*

**(DESCRITIVO — APAGAR APÓS INSERIR IMAGEM: painel do Grafana com dois gráficos de séries temporais lado a lado — CPU usage e memory working set — do pod `clickhouse-shard0-0` do namespace warehouse durante uma janela de aproximadamente 15 minutos cobrindo uma execução completa do `fhvhv_pipeline`, evidenciando o pico de CPU durante ingestão e OPTIMIZE FINAL e o patamar estável de memória bem abaixo do limite de 24 GiB do nó.)**

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

A análise a seguir consolida 54 amostras por camada em cada pergunta, acumuladas ao longo de dez execuções independentes da DAG.

*Tabela 4 — Q1: receita diária de 2023, médias sobre 54 amostras (10 execuções × 5 iterações)*

| Camada | Engine avg (ms) | Read rows | Read bytes | Memory peak | Speedup vs bronze |
|---|---:|---:|---:|---:|---:|
| bronze | 26.315 | 210.963.166 | 14,15 GiB | 44,3 MiB | 1,0× (linha-base) |
| silver | 4.872 | 232.410.875 | 3,03 GiB | 16,7 MiB | 5,4× |
| gold | 4,2 | 365 | 7,13 KiB | 0 B | ≈6.266× |

Fonte: Resultados originais da pesquisa

*Tabela 5 — Q2: top 10 pares origem-destino por borough, médias sobre 54 amostras (10 execuções × 5 iterações)*

| Camada | Engine avg (ms) | Read rows | Read bytes | Memory peak | Speedup vs bronze |
|---|---:|---:|---:|---:|---:|
| bronze | 52.544 | 210.963.696 | 17,68 GiB | 120,9 MiB | 1,0× (linha-base) |
| silver | 31.459 | 232.411.405 | 2,38 GiB | 45,3 MiB | 1,7× |
| gold | 12,4 | 45 | 765 B | 320 B | ≈4.237× |

Fonte: Resultados originais da pesquisa

O salto de desempenho entre bronze e gold ultrapassou três ordens de grandeza em ambas as perguntas. A diferença é explicada por três fatores complementares: o *scan* do *engine*, em que bronze e silver leram centenas de milhões de linhas enquanto gold acessou tabelas pré-agregadas com poucas centenas ou poucas dezenas de linhas; o volume de I/O, que caiu de 14 a 18 GiB no bronze para menos de 10 KiB no gold; e a ausência de operações por linha no gold, uma vez que agregações, conversões de tipo e *joins* já foram executadas durante a carga. O resultado validou empiricamente a arquitetura *medallion*: a camada gold materializada pelo dbt transformou consultas analíticas da ordem de dezenas de segundos para a ordem de milissegundos, viabilizando *dashboards* interativos e análises ad-hoc sobre o mesmo conjunto de dados bruto. A *task* `report_history` da DAG computa média, desvio-padrão e coeficiente de variação sobre todo o histórico persistido, permitindo avaliar a consistência *cross-run* das medições conforme novas execuções são acumuladas.

<!-- FIGURA 7 — INSERIR IMAGEM AQUI
Captura: saída do log da task `consolidate_results` ou `report_history` da DAG benchmark_medallion, mostrando a tabela formatada com as três camadas lado a lado, o speedup calculado e, idealmente, o bloco de estatística cross-run com CV%.
Onde capturar: Airflow UI > DAGs > benchmark_medallion > última execução > task consolidate_results (ou report_history) > Logs.
O que destacar: as linhas mostrando engine_avg_ms por camada, o speedup numérico (Q1 ≈6.266× e Q2 ≈4.237×) e, se o print incluir, a coluna CV% demonstrando consistência <20% nas medições. Pode-se alternativamente capturar o grafo da DAG `benchmark_medallion` com as sete tasks em verde, evidenciando a orquestração da metodologia.
Formato: PNG do bloco de texto tabular, sem crop excessivo. -->

*Figura 7 — Relatório consolidado do benchmark medallion com speedups por camada e consistência cross-run*

**(DESCRITIVO — APAGAR APÓS INSERIR IMAGEM: saída textual tabular da task `consolidate_results` ou `report_history` da DAG benchmark_medallion, mostrando as três camadas bronze, silver e gold lado a lado com as colunas engine_avg, read_bytes e speedup, numericamente evidenciando o ganho de aproximadamente seis mil vezes para Q1 e quatro mil vezes para Q2, e — se visível no print — o bloco cross-run com coeficiente de variação inferior a vinte por cento por camada.)**

Fonte: Resultados originais da pesquisa

**Portabilidade e análise comparativa com plataforma gerenciada**

O objetivo desta análise não foi determinar qual plataforma apresenta maior desempenho bruto — uma comparação direta entre um cluster de nuvem e um ambiente auto-hospedado em nó único não seria justa nem informativa. O objetivo foi evidenciar os *trade-offs* entre as duas abordagens em dimensões relevantes para a tomada de decisão: custo, complexidade operacional, portabilidade, controle e governança. A portabilidade foi validada experimentalmente por meio do princípio de *adapter swapping* do dbt: o mesmo projeto analítico — modelos SQL, testes, *sources* e geração de *docs* — foi instanciado em um segundo ambiente Databricks substituindo o *adapter* `dbt-clickhouse` por `dbt-databricks` no `profiles.yml`, com adaptações mínimas de dialeto (`toDate(...)` → `to_date(...)`, `toDateTime(...)` → `to_timestamp(...)`, `toFloat64(...)` → `CAST(... AS DOUBLE)`, e a diretiva de otimização `OPTIMIZE TABLE FINAL` substituída pelo equivalente `OPTIMIZE` do Spark SQL). O exercício confirmou que modelos, testes e linhagem migram entre plataformas sem reescrita arquitetural, validando o dbt como camada de desacoplamento.

*Tabela 6 — Análise comparativa qualitativa entre stack open source e plataforma Databricks*

| Dimensão | Stack open source (K3s) | Databricks |
|---|---|---|
| Custo de licenciamento | Zero | Por DBU consumida |
| Custo de infraestrutura mensal estimado | Baixo (VM em hipervisor próprio) | Variável com uso (cluster e armazenamento) |
| Tempo de *setup* inicial | Da ordem de horas (K3s, Argo CD e Helm) | Da ordem de minutos (*workspace* e *upload*) |
| Monitoramento embutido | Prometheus e Grafana, 15 *dashboards* | *Spark UI* e *Databricks Monitoring* |
| Orquestração | Apache Airflow e *Astronomer Cosmos* | *Databricks Workflows* |
| Governança e linhagem | dbt tests e dbt docs | dbt e *Unity Catalog* |
| Portabilidade entre plataformas | Qualquer cluster Kubernetes | Dependência da plataforma Databricks |
| Controle de infraestrutura | Total, via *GitOps* e infraestrutura própria | Parcial, plataforma gerenciada |
| Escalabilidade | Manual, por adição de nós ao cluster | Automática |
| Reutilização do projeto dbt | Nativa | Validada com troca de *adapter* |

Fonte: Resultados originais da pesquisa

A comparação evidenciou situações em que cada abordagem se mostra vantajosa. A abordagem auto-hospedada em Kubernetes favorece cenários que exigem controle total da infraestrutura, previsibilidade de custos, ausência de dependência de fornecedor e governança totalmente auditável via *GitOps*. A plataforma gerenciada favorece cenários que priorizam *time-to-value* reduzido, escalabilidade automática e governança embutida via *Unity Catalog*. A portabilidade do projeto dbt entre as duas configurações, confirmada pela troca de *adapter*, indicou que a escolha da plataforma de execução pode ser revista ao longo do ciclo de vida do produto analítico sem perda do investimento feito em modelagem, testes e documentação. Isso corrobora a recomendação de Reis e Housley (2022) por ferramentas desacopladas como princípio de arquitetura de dados moderna.

**Delimitação do escopo experimental**

A avaliação desta pesquisa concentrou-se nos dois eixos de maior valor analítico em relação às lacunas apontadas no ciclo preliminar: indicadores quantitativos do pipeline ponta a ponta (Tabela 2), propriedades físicas das camadas materializadas (Tabela 3) e o ganho mensurável da arquitetura *medallion* em duas perguntas de negócio semanticamente equivalentes (Tabelas 4 e 5). Duas frentes complementares de avaliação — escalabilidade por volume de dados com estratégias de recarga total *versus* incremental, e comportamento sob carga concorrente com diferentes níveis de *threads* — foram mapeadas na fase de planejamento como trabalho futuro, uma vez que a arquitetura *medallion* já constitui um experimento multicenário com três camadas e duas perguntas, sustentando estatisticamente a evidência principal com dez execuções cumulativas e coeficientes de variação inferiores a 20%.

---

## Conclusão

Os resultados apresentados demonstraram a viabilidade técnica e o desempenho competitivo de uma stack moderna de engenharia de dados construída exclusivamente com tecnologias *open source*. A escolha do K3s em configuração *single-node* mostrou-se eficiente para a Prova de Conceito, otimizando o uso de recursos e simplificando a gestão do ambiente. A adoção do Argo CD para o *deploy* da infraestrutura e a sincronização automática de manifestos, DAGs e modelos dbt reforçaram as práticas de *GitOps*, garantindo automação, consistência e reprodutibilidade.

A implementação completa do projeto dbt segundo a arquitetura *medallion* consolidou a stack como uma plataforma analítica madura, capaz de processar dados reais em escala da ordem de centenas de milhões de registros com governança, testes automatizados e documentação rastreável. A integração nativa com Airflow via *Astronomer Cosmos* ofereceu visibilidade ponta a ponta do pipeline, *retries* granulares e *lineage* visual diretamente no grafo da DAG.

Os indicadores quantitativos coletados via *benchmark* evidenciaram o ganho mensurável da arquitetura *medallion*, com consultas na camada gold executando em ordens de grandeza menos tempo do que sobre a camada bronze em ambas as perguntas avaliadas, corroborando empiricamente a recomendação da arquitetura *multi-hop* para *lakehouses* analíticos. A análise comparativa qualitativa com a plataforma Databricks, combinada com a validação experimental da portabilidade do projeto dbt entre as duas plataformas, forneceu subsídios objetivos para decisões de arquitetura entre soluções auto-hospedadas e gerenciadas.

A combinação entre uma infraestrutura *cloud-native* leve, gerenciamento *GitOps*, orquestração robusta, armazenamento compatível com S3, processamento analítico de alto desempenho e transformações governadas resultou em uma arquitetura pronta para uso em projetos reais de engenharia de dados, validando o objetivo central do trabalho.

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

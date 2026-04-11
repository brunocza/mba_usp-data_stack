# MBA USP — Data Stack on k3s

Stack de dados completa rodando em um k3s single-node como projeto de TCC do MBA USP. Orquestração GitOps via ArgoCD, ingest/transform via Airflow+dbt, warehouse ClickHouse, data lake MinIO, observabilidade Prometheus+Grafana e exposição segura via Cloudflare Tunnel + Zero Trust Access.

## Arquitetura

```
         ┌─────────────────┐                              ┌────────────────┐
Browser →│ Cloudflare Edge │→ Tunnel (cloudflared pods) →│  k3s cluster   │
         └─────────────────┘                              └────────────────┘
               ↑                                          │
        Zero Trust Access (OTP)                           ├─ ArgoCD (GitOps)
                                                          ├─ Airflow 3.1.8
                                                          │    └─ dbt_demo (ClickHouse)
                                                          ├─ ClickHouse (warehouse)
                                                          ├─ MinIO (data lake + S3 API)
                                                          ├─ Prometheus + Grafana
                                                          └─ cloudflared
```

**Componentes:**

- **Kubernetes**: k3s v1.32 single-node, MetalLB para LoadBalancers internos (192.168.18.21–58)
- **GitOps**: ArgoCD com `automated.selfHeal=true` — qualquer coisa no cluster é reconciliada a partir deste repo
- **Orchestration**: Apache Airflow 3.1.8 com CeleryExecutor, git-sync lendo [dags/](dags/) deste repo
- **Transformação**: dbt-core + dbt-clickhouse
- **Warehouse**: ClickHouse (chart Bitnami)
- **Data lake**: MinIO operator + tenant
- **Observabilidade**: Prometheus (com kube-state-metrics + node-exporter) + Grafana com dashboards provisionados
- **Exposição pública**: Cloudflare Tunnel (`k3s-tcc`) → hostnames em `*.bxdatalab.com` protegidos por Cloudflare Access

## Aplicações públicas

| App | URL | Notas |
|---|---|---|
| Airflow | https://airflow.bxdatalab.com | DAGs via git-sync de [dags/](dags/) |
| Grafana | https://grafana.bxdatalab.com | Dashboards provisionados em folders Cluster / Airflow / ClickHouse / MinIO |
| ArgoCD | https://argocd.bxdatalab.com | Source of truth pra tudo no cluster |
| MinIO Console | https://minio.bxdatalab.com | UI do data lake |
| MinIO S3 API | https://s3.bxdatalab.com | Endpoint S3 (path-style) |
| dbt docs | https://dbt-docs.bxdatalab.com | Docs auto-geradas pelo sidecar |

Todas protegidas por Cloudflare Zero Trust Access com política `allowed-users` (email OTP). Prometheus intencionalmente **não é** exposto publicamente — só acessível de dentro do cluster.

Credenciais de login e detalhes de rede interna: ver `ENDERECOS-CLUSTER.md` (não commitado).

## Layout do repositório

```
.
├── infra/src/
│   ├── app-manifests/          # ArgoCD Application CRs (sources of truth)
│   │   ├── deepstorage/        # minio-operator + minio-tenant
│   │   ├── monitorability/     # grafana + prometheus
│   │   ├── orchestrator/       # airflow
│   │   └── warehouse/          # clickhouse
│   ├── helm-charts/            # Helm charts vendorados (o que ArgoCD instala)
│   │   ├── airflow-official/   # Apache Airflow chart 1.20.0
│   │   ├── clickhouse/         # Bitnami ClickHouse
│   │   ├── minio-{operator,tenant}/
│   │   ├── grafana/            # Grafana chart 8.5.1 + dashboards JSON vendorados
│   │   └── prometheus/         # Prometheus chart 25.27.0
│   └── k8s-manifests/
│       └── cloudflared/        # Deployment do tunnel
│
├── dags/                       # Airflow DAGs (lidas via git-sync)
│   ├── example_dag.py
│   ├── dbt_demo_dag.py         # roda dbt_demo/ contra ClickHouse
│   └── dbt_demo/               # projeto dbt (models, profiles, schema)
│
├── dev/                        # [GITIGNORED] sandbox de desenvolvimento dbt
│   ├── dbt_sandbox/            # cópia editável do dbt_demo → schema dbt_sandbox
│   ├── activate.sh             # source isso pra ativar venv + env vars
│   └── README.md
│
├── proxmox_vm_template/        # Terraform/config da VM base no Proxmox
├── ENDERECOS-CLUSTER.md        # [GITIGNORED] credenciais + URLs internas
├── .mcp.json                   # [GITIGNORED] config MCP (Airflow + Grafana)
└── README.md                   # este arquivo
```

## Workflow de mudanças (git-first)

Todas as mudanças na infra ou nas DAGs passam por:

1. **Edita localmente** (`infra/src/helm-charts/<app>/values.yaml` ou `dags/*.py`)
2. **Commit + push** (`git commit` + VSCode Sync Changes, sem `git push` CLI — não há credenciais configuradas)
3. **ArgoCD reconcilia** automaticamente (self-heal ligado em todos os apps)
4. **Observa** via MCP do ArgoCD ou `kubectl -n argocd get applications`

❌ Não faça `kubectl patch` direto em resources gerenciados pelo ArgoCD — o self-heal reverte em segundos.

Exceções legítimas:

- Secrets de credenciais são criados out-of-band via `kubectl create secret` (não commitados)
- Application CRs foram aplicados manualmente via `kubectl apply` (não há app-of-apps ainda)
- Patches emergenciais (ex.: deletar pod redis stale) — não afetam a spec do Deployment

## Desenvolvimento local com dbt

Sandbox isolado em `dev/dbt_sandbox/` (gitignored) contra o schema `dbt_sandbox` do ClickHouse — não afeta o `dbt_demo` que o Airflow popula.

```bash
# Setup uma vez
uv venv ~/.venvs/dbt-dev --python 3.12
uv pip install --python ~/.venvs/dbt-dev/bin/python "dbt-core~=1.8.0" "dbt-clickhouse~=1.8.0"

# Toda sessão
cd /home/ubuntu/mba_usp-data_stack
source dev/activate.sh
cd dev/dbt_sandbox
dbt debug    # All checks passed!
dbt run      # cria models no schema dbt_sandbox
dbt test
```

Quando um model amadurece, copia pra `dags/dbt_demo/models/` e commita — o git-sync do Airflow pega em <10s.

## Monitoração

Grafana lê do Prometheus in-cluster e expõe dashboards provisionados:

- **Cluster**: Node Exporter Full, Kubernetes Cluster Overview, Pods
- **Airflow**: Airflow monitoring (FAB DB + statsd), Airflow cluster
- **ClickHouse**: dashboard oficial 14192
- **MinIO**: MinIO Cluster (13502), MinIO Bucket (19237)

Targets scrapeados por Prometheus (em [infra/src/helm-charts/prometheus/values.yaml](infra/src/helm-charts/prometheus/values.yaml) → `extraScrapeConfigs`):

- `airflow-statsd` → `airflow10-statsd.orchestrator2:9102`
- `clickhouse` → `clickhouse.warehouse:8001` (métricas do Bitnami chart)
- `minio-cluster` + `minio-node` → `minio.deepstorage:80/minio/v2/metrics/*` (anonymous via `MINIO_PROMETHEUS_AUTH_TYPE=public`)
- Cluster vem automático via kube-state-metrics + node-exporter do chart prometheus

## Segurança

- **Cloudflare Zero Trust Access** em todos os hostnames públicos — OTP por email antes de qualquer login app
- **Bot Fight Mode** ativo na zone
- **Prometheus** não exposto publicamente
- **Secrets**: credenciais em K8s secrets out-of-band (nunca em git)
  - `orchestrator2/clickhouse-credentials` — dbt profile via `env_var()`
  - `monitorability/grafana-admin` — Grafana admin password
  - `orchestrator2/airflow10-stable-{redis,fernet,jwt,websec,api}` — senhas fixas pra não rerolar em cada sync
  - `cloudflared/cloudflared-token` — tunnel token
- **.gitignore**: chaves SSH (`id_ed25519*`), `.claude/`, `.mcp.json`, `ENDERECOS-CLUSTER.md`, `dev/`

## Troubleshooting

Problemas recorrentes e suas soluções:

- **Git-sync 404 em pods antigos**: existia `search com` no netplan do nó — pods criados antes do fix têm `/etc/resolv.conf` congelado. Delete o pod pra o STS recriar.
- **Senhas regeradas a cada sync**: o chart Airflow usa `randAlphaNum` em helm templates, que não é determinístico sob `helm template` (client-side). Pinamos secrets via `*SecretName` para secrets externos estáveis.
- **Grafana perdendo SA tokens**: sem PVC, toda reinicialização zera a sqlite. Ativamos `persistence.enabled=true`.
- **Dashboards com `${DS_PROMETHEUS}`**: o chart não resolve essa variável em template — pinamos UID `prometheus` no datasource e pré-processamos os JSONs.
- **ConfigMap > 3 MB ao provisionar dashboards**: Kubernetes limita objetos a 3 MiB; split em múltiplos providers (`cluster`, `airflow`, `clickhouse`, `minio`) + `ServerSideApply=true` na Application ArgoCD.

## Requisitos para reprovisionar

Quem quiser reconstruir do zero num k3s próprio:

1. Criar a VM (ver `proxmox_vm_template/`)
2. Instalar k3s + MetalLB + ArgoCD (manual, não automatizado ainda — TODO: fazer um bootstrap script)
3. `kubectl apply -f infra/src/app-manifests/**/*.yaml` pra criar as Applications
4. Criar secrets out-of-band (lista em `ENDERECOS-CLUSTER.md` → seção "Recuperando credenciais")
5. Criar Cloudflare Tunnel + Zero Trust Applications
6. Configurar DNS apontando pra CF

## Links úteis

- Histórico de implementação: `git log --oneline`
- Memória persistente do Claude Code: `.claude/projects/-home-ubuntu-mba-usp-data-stack/memory/` (gitignored)

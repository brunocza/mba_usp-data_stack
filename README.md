# MBA USP — Data Stack on k3s

> Plataforma de dados completa em um cluster Kubernetes single-node, provisionada com Terraform sobre Proxmox VE, gerenciada via GitOps com ArgoCD, e desenvolvida como trabalho de conclusão do curso **MBA em Data Science & Analytics — ICMC/USP**.

Este repositório contém **toda a infraestrutura como código** do projeto: desde o provisionamento da VM base no Proxmox, passando pela instalação do k3s e MetalLB, até a implantação declarativa dos serviços de dados (Airflow, ClickHouse, MinIO, dbt, Grafana, Prometheus) e a exposição pública controlada via Cloudflare Tunnel com autenticação Zero Trust.

O objetivo didático é demonstrar, de ponta a ponta, como montar uma plataforma de dados **realista, reproduzível e observável** usando ferramentas open-source e práticas modernas de *platform engineering*.

---

## Índice

1. [Visão geral da arquitetura](#visão-geral-da-arquitetura)
2. [Stack de tecnologias](#stack-de-tecnologias)
3. [Aplicações expostas](#aplicações-expostas)
4. [Layout do repositório](#layout-do-repositório)
5. [Workflow de mudanças (git-first)](#workflow-de-mudanças-git-first)
6. [Desenvolvimento local com dbt](#desenvolvimento-local-com-dbt)
7. [Observabilidade](#observabilidade)
8. [Segurança](#segurança)
9. [Troubleshooting](#troubleshooting)
10. [Provisionamento do zero](#provisionamento-do-zero)

---

## Visão geral da arquitetura

```
                                  Internet
                                     │
                      ┌──────────────▼──────────────┐
                      │      Cloudflare Edge        │
                      │  (TLS + DNS + Zero Trust)   │
                      └──────────────┬──────────────┘
                                     │  (Tunnel outbound)
                      ┌──────────────▼──────────────┐
                      │    cloudflared pods (x2)    │
                      │   namespace: cloudflared    │
                      └──────────────┬──────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
┌────────▼────────┐        ┌─────────▼─────────┐       ┌─────────▼─────────┐
│    ArgoCD       │        │    Airflow 3.1    │       │    Grafana        │
│    (GitOps)     │◀───────│ (Celery+git-sync) │──────▶│  (dashboards      │
└────────┬────────┘        └─────────┬─────────┘       │   provisionados)  │
         │                           │                 └─────────┬─────────┘
         │ reconcilia                │ executa DAGs              │ consulta
         ▼                           ▼                           ▼
┌─────────────────┐        ┌───────────────────┐       ┌───────────────────┐
│  helm charts    │        │     dbt_demo      │       │    Prometheus     │
│  neste repo     │        │  (project inline) │       │  (scrape in-clu)  │
└─────────────────┘        └─────────┬─────────┘       └───────────────────┘
                                     │
                         ┌───────────┼───────────┐
                         ▼                       ▼
                ┌────────────────┐      ┌────────────────┐
                │   ClickHouse   │      │     MinIO      │
                │   (warehouse)  │      │  (data lake)   │
                └────────────────┘      └────────────────┘
```

O tráfego do navegador jamais toca diretamente o cluster: ele passa pela edge do Cloudflare, é autenticado via Zero Trust Access, e então desce pelo túnel até os pods do `cloudflared`. A partir daí, atinge os Services internos via DNS do Kubernetes. Isso elimina a necessidade de IP público, port-forward ou VPN — e entrega TLS automático como bônus.

---

## Stack de tecnologias

| Camada | Tecnologia | Versão | Papel |
|---|---|---|---|
| **Virtualização** | Proxmox VE + Terraform (`Telmate/proxmox`) | 3.0.1-rc1 | Provisiona a VM Ubuntu 22.04 a partir de um template cloud-init |
| **Orquestração de containers** | k3s | v1.32.5+k3s1 | Distribuição leve de Kubernetes |
| **Load balancer interno** | MetalLB | v0.13.12 | Atribui IPs de um pool reservado na rede local para Services do tipo `LoadBalancer` |
| **GitOps** | ArgoCD | | Reconcilia continuamente o estado do cluster com este repositório |
| **Tunnel & autenticação** | Cloudflare Tunnel + Zero Trust Access | latest | Exposição pública sem porta aberta, com OTP por email |
| **Orquestração de workflows** | Apache Airflow | 3.1.8 (chart 1.20.0) | DAGs sincronizadas via git-sync, executor Celery + Redis |
| **Transformação de dados** | dbt-core + dbt-clickhouse | ~1.8.0 | Project `dags/dbt_demo/` materializa models em ClickHouse |
| **Warehouse** | ClickHouse (chart Bitnami) | | Armazenamento analítico colunar |
| **Data lake** | MinIO (operator + tenant) | | Object storage compatível com S3, bucket policies nativas |
| **Métricas** | Prometheus + node-exporter + kube-state-metrics | 25.27.0 / 2.54.1 | Coleta de métricas do cluster e das aplicações |
| **Dashboards** | Grafana | 8.5.1 / app 11.2 | Visualização, com dashboards provisionados via ConfigMap |

---

## Aplicações expostas

Todas servidas sob `*.bxdatalab.com` via Cloudflare Tunnel e protegidas por Zero Trust Access (exceto onde indicado):

| Aplicação | URL | Protegido por Access? |
|---|---|---|
| Airflow | `https://airflow.bxdatalab.com` | ✅ |
| Grafana | `https://grafana.bxdatalab.com` | ✅ |
| ArgoCD | `https://argocd.bxdatalab.com` | ✅ |
| MinIO Console | `https://minio.bxdatalab.com` | ✅ |
| MinIO S3 API | `https://s3.bxdatalab.com` | ❌ (requer chamadas programáticas S3/SigV4) |
| dbt docs | `https://dbt-docs.bxdatalab.com` | ❌ (documentação pública) |

**Prometheus** propositalmente não é exposto à internet — é consultado somente de dentro do cluster pelo Grafana, reduzindo a superfície de ataque.

---

## Layout do repositório

```
.
├── proxmox_vm_template/        # Terraform: provisiona a VM no Proxmox
│   ├── main.tf                 # resource proxmox_vm_qemu "K3S-TCC"
│   ├── variables.tf            # entradas configuráveis (CPU, RAM, IP, etc.)
│   └── install_k3s.sh          # script bootstrap do k3s dentro da VM
│
├── infra/
│   ├── terraform/              # Terraform Day-2 do cluster
│   │   └── kubernetes/
│   │       ├── bare_metal_config/    # MetalLB + Kube-VIP + IPAddressPool
│   │       └── pv/                    # Persistent Volumes via NFS (opcional)
│   │
│   └── src/
│       ├── app-manifests/      # ArgoCD Applications (fonte da verdade)
│       │   ├── deepstorage/    # minio-operator + minio-tenant
│       │   ├── monitorability/ # grafana + prometheus
│       │   ├── orchestrator/   # airflow
│       │   └── warehouse/      # clickhouse
│       │
│       ├── helm-charts/        # Helm charts vendorados que o ArgoCD instala
│       │   ├── airflow-official/   # Apache Airflow 1.20.0
│       │   ├── clickhouse/         # Bitnami ClickHouse
│       │   ├── minio-operator/
│       │   ├── minio-tenant/
│       │   ├── grafana/            # + dashboards JSON vendorados
│       │   └── prometheus/         # + node-exporter + kube-state-metrics
│       │
│       └── k8s-manifests/
│           └── cloudflared/    # Deployment do túnel Cloudflare
│
├── dags/                       # DAGs do Airflow (lidas via git-sync)
│   ├── example_dag.py
│   ├── dbt_demo_dag.py         # pipeline que executa dbt_demo/
│   └── dbt_demo/               # projeto dbt completo (models, profiles, schema)
│
├── dev/                        # [gitignored] sandbox local de desenvolvimento dbt
│
└── README.md                   # este arquivo
```

---

## Workflow de mudanças (git-first)

O princípio fundamental da operação deste cluster é: **o estado desejado vive no Git**. Nada deve ser aplicado diretamente via `kubectl` em recursos gerenciados pelo ArgoCD — qualquer divergência é detectada e revertida automaticamente pelo `selfHeal`.

O ciclo de uma alteração típica:

1. **Edite** o arquivo relevante (ex: `infra/src/helm-charts/grafana/values.yaml` ou `dags/dbt_demo/models/example/first_model.sql`).
2. **Commit** localmente com uma mensagem descritiva.
3. **Push** para o remoto via *VSCode Sync Changes* (`git push` CLI não está configurado intencionalmente — obriga passar pelo fluxo revisado).
4. **ArgoCD** detecta a mudança na branch `main` em até 3 minutos e reconcilia o cluster. Para DAGs, o git-sync do Airflow faz o pull a cada 5 segundos.
5. **Observe** o resultado via `kubectl -n argocd get applications` ou pelos MCP servers configurados (Airflow e Grafana).

**Exceções legítimas ao git-first:**

- **Segredos**: credenciais são criadas *out-of-band* via `kubectl create secret` para não vazar no git. O chart refere-se a elas por nome (`*SecretName`).
- **Application CRs**: foram aplicadas manualmente com `kubectl apply` pois o padrão *app-of-apps* ainda não está implementado (próximo passo do projeto).
- **Patches emergenciais**: deletar um pod travado é OK — isso não altera a *spec* do Deployment, então o ArgoCD não reverte.

---

## Desenvolvimento local com dbt

Para iterar em models dbt sem precisar passar por commit + sync a cada experimento, o repositório oferece um *sandbox* isolado em `dev/dbt_sandbox/`. Ele é ignorado pelo git e escreve no schema `dbt_sandbox` do ClickHouse — totalmente separado do `dbt_demo` que o Airflow popula em produção.

### Setup (uma vez)

```bash
# Python venv com dbt-core e dbt-clickhouse
uv venv ~/.venvs/dbt-dev --python 3.12
uv pip install --python ~/.venvs/dbt-dev/bin/python \
  "dbt-core~=1.8.0" "dbt-clickhouse~=1.8.0"
```

### Ciclo de trabalho

```bash
cd /home/ubuntu/mba_usp-data_stack
source dev/activate.sh           # ativa venv + exporta CLICKHOUSE_* e DBT_PROFILES_DIR
cd dev/dbt_sandbox

dbt debug                        # valida conexão:  "All checks passed!"
dbt run                          # materializa os models no schema dbt_sandbox
dbt test                         # roda tests de not_null / unique / relationships
```

Quando um model amadurece, basta copiá-lo para `dags/dbt_demo/models/` e commitar. O git-sync do Airflow captura a mudança em segundos e a DAG `dbt_demo_dag` passa a executá-lo no próximo trigger.

---

## Observabilidade

O Grafana é provisionado com quatro *folders* de dashboards, cada um alimentado por uma ConfigMap separada para ficar abaixo do limite de 3 MiB do Kubernetes API:

| Folder | Dashboards | Fonte |
|---|---|---|
| **Cluster** | Node Exporter Full, Kubernetes Cluster Overview, Kubernetes Pods | grafana.com IDs 1860, 7249, 6417 |
| **Airflow** | Airflow monitoring, Airflow cluster dashboard | IDs 14448, 20994 |
| **ClickHouse** | ClickHouse | ID 14192 |
| **MinIO** | MinIO Cluster, MinIO Bucket | IDs 13502, 19237 |

Os JSONs são *vendorados* em `infra/src/helm-charts/grafana/dashboards/` (não baixados em runtime) porque o campo `gnetId` do chart só é processado pelo `helm install`, e não pelo `helm template` usado pelo ArgoCD.

Os *scrape targets* adicionais do Prometheus estão em `infra/src/helm-charts/prometheus/values.yaml` → `extraScrapeConfigs`:

- `airflow-statsd` → `airflow10-statsd.orchestrator2:9102`
- `clickhouse` → `clickhouse.warehouse:8001` (métricas nativas do chart Bitnami)
- `minio-cluster` + `minio-node` → `minio.deepstorage:80/minio/v2/metrics/*` (acesso anônimo habilitado via `MINIO_PROMETHEUS_AUTH_TYPE=public`)
- Métricas do cluster vêm automaticamente via `kube-state-metrics` e `node-exporter` empacotados como subcharts do Prometheus.

---

## Segurança

### Exposição controlada

- **Cloudflare Zero Trust Access** em todos os hostnames públicos: o usuário recebe um código OTP por email antes sequer de ver a tela de login da aplicação, o que inviabiliza ataques de *credential stuffing* e força bruta.
- **Bot Fight Mode** ativo na zona, bloqueando automaticamente crawlers maliciosos.
- **Prometheus** não é roteado pelo túnel — permanece acessível somente via DNS interno do cluster.

### Segredos

Nenhuma credencial é armazenada no git. Todos os segredos vivem em *K8s Secrets* criados fora do fluxo do ArgoCD, e os charts os referenciam por nome:

| Secret | Namespace | Conteúdo |
|---|---|---|
| `clickhouse-credentials` | `orchestrator2` | User/password do ClickHouse consumidos pelo profile dbt via `env_var()` |
| `grafana-admin` | `monitorability` | Credenciais do admin do Grafana |
| `airflow10-stable-{redis,fernet,jwt,websec,api}` | `orchestrator2` | Senhas fixas do Airflow (evita rerroll em cada sync) |
| `cloudflared-token` | `cloudflared` | Token do túnel |

### Gitignore defensivo

O `.gitignore` bloqueia por padrão: chaves SSH privadas (`id_ed25519*`), diretórios de tooling local (`.claude/`, `dev/`), arquivos de configuração MCP (`.mcp.json`) e documentos com credenciais em texto plano.

---

## Troubleshooting

Durante o desenvolvimento, alguns problemas recorrentes foram encontrados e documentados aqui como referência:

| Sintoma | Causa | Solução |
|---|---|---|
| Pods antigos falham no git-sync com `Network is unreachable` | `search com` antigo no `/etc/resolv.conf` do nó polui `ndots:5`, fazendo `github.com` resolver como `github.com.com` | Corrigir netplan no nó e deletar pods antigos; StatefulSets recriam com config limpa |
| Senhas regeradas a cada sync do ArgoCD | O chart do Airflow usa `randAlphaNum` em templates Helm, que não é determinístico sob `helm template` (client-side) | Pinar via `*SecretName` apontando para Secrets externos estáveis |
| Grafana perde SA tokens e admin password a cada restart | Ausência de PVC faz a sqlite viver em `emptyDir` | `persistence.enabled=true` no chart |
| Dashboards com `${DS_PROMETHEUS}` não resolvido | O template do chart não processa essa variável de input | Pinar UID `prometheus` no datasource provisionado e substituir `${DS_PROMETHEUS}` pelos JSONs via `sed` antes de vendorar |
| ConfigMap de dashboards > 3 MiB | Kubernetes limita objetos do API server a 3 MiB | Dividir em múltiplos *providers* (`cluster`, `airflow`, `clickhouse`, `minio`) e habilitar `ServerSideApply=true` na Application do ArgoCD |
| Celery falha com `invalid username-password pair` no Redis | Secret regerado mas pod Redis não foi reiniciado, mantendo a senha antiga em memória | Delete o pod Redis; o StatefulSet o recria lendo o Secret atual |

---

## Provisionamento do zero

Esta seção descreve como recriar o projeto em um ambiente limpo, começando por um host Proxmox e terminando com a plataforma acessível publicamente. Os passos foram pensados para serem didáticos — cada etapa pode ser executada e verificada isoladamente.

### Pré-requisitos

- Um host Proxmox VE com acesso administrativo e uma rede privada disponível (faixa ajustável em `variables.tf`)
- Um template cloud-init de Ubuntu 22.04 já cadastrado no Proxmox (nome usado em `vm_ubuntu_tmpl_name`)
- Uma conta Cloudflare com um domínio ativo (zona com nameservers apontando para `*.ns.cloudflare.com`)
- `terraform`, `kubectl` e `helm` instalados na estação de trabalho

### Etapa 1 — Provisionar a VM (`proxmox_vm_template/`)

O manifesto Terraform em `proxmox_vm_template/main.tf` cria um recurso `proxmox_vm_qemu "K3S-TCC"` clonando o template cloud-init especificado. Ele aceita dimensões de CPU/RAM/disco como variáveis (`variables.tf`) e configura rede estática, chaves SSH e o usuário cloud-init.

```bash
cd proxmox_vm_template

# Crie terraform.tfvars com os parâmetros do seu ambiente
# (NÃO commitar — o .gitignore já cobre *.tfvars)
cat > terraform.tfvars <<'EOF'
pm_api_url          = "https://<proxmox-host>:8006/api2/json"
pm_api_token_id     = "<token-id>"
pm_api_token_secret = "<token-secret>"
pm_host             = "<proxmox-node-name>"
vm_ubuntu_tmpl_name = "<nome-do-template-cloud-init>"
vm_cores            = 8
vm_vcpus            = 8
vm_sockets          = 1
vm_cpu_type         = "host"
vm_memory           = 32768      # 32 GiB
vm_disk_size        = 100        # GiB
vm_ip_base          = "<ip-estatico-desejado>"
vm_gateway          = "<gateway-da-rede>"
vm_user             = "<usuario-cloudinit>"
ssh_public_keys     = "<chave-publica-ssh-em-base64>"
EOF

terraform init
terraform plan
terraform apply
```

O provisionamento também faz `remote-exec` pra instalar docker no primeiro boot (passo herdado de uma versão anterior; para k3s puro é dispensável).

### Etapa 2 — Instalar o k3s (`proxmox_vm_template/install_k3s.sh`)

Com a VM no ar, execute o script de bootstrap dentro dela. Ele:

1. Atualiza o sistema
2. Desabilita swap (requisito do Kubernetes)
3. Ajusta parâmetros de rede (`net.bridge.bridge-nf-call-*`, `ip_forward`)
4. Instala a versão estável atual do k3s com `--write-kubeconfig-mode 644`
5. Cria um symlink `/usr/local/bin/kubectl` → `/usr/local/bin/k3s`

```bash
NODE_IP="<ip-da-vm-recem-criada>"
NODE_USER="<usuario-ssh>"

scp proxmox_vm_template/install_k3s.sh "$NODE_USER@$NODE_IP:/tmp/"
ssh "$NODE_USER@$NODE_IP" "sudo bash /tmp/install_k3s.sh"

# Valide
ssh "$NODE_USER@$NODE_IP" "kubectl get nodes -o wide"
```

### Etapa 3 — MetalLB & IPAddressPool (`infra/terraform/kubernetes/bare_metal_config/`)

Este diretório contém o script `setup-load-balancer.sh` que instala **Kube-VIP** (cloud controller), aplica o manifest do **MetalLB v0.13.12** e configura o pool de IPs.

O pool de IPs é declarado em `metallb-config.yaml`. Ajuste a faixa para refletir a sub-rede livre no seu ambiente antes de aplicar — o valor padrão do repositório aponta para uma rede privada interna e deve ser trocado em cada deployment:

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: first-pool
  namespace: metallb-system
spec:
  addresses:
    - <faixa-de-ips-livre-na-sua-lan>   # ex.: 10.0.0.100-10.0.0.150
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default-l2-advertisement
  namespace: metallb-system
spec:
  ipAddressPools:
    - first-pool
```

```bash
bash infra/terraform/kubernetes/bare_metal_config/setup-load-balancer.sh
kubectl apply -f infra/terraform/kubernetes/bare_metal_config/metallb-config.yaml
```

### Etapa 4 — Instalar o ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### Etapa 5 — Criar os Secrets out-of-band

Antes de aplicar as Applications, crie as credenciais que os charts esperam referenciar por nome:

```bash
# Exemplo: ClickHouse para dbt
kubectl create namespace orchestrator2
kubectl -n orchestrator2 create secret generic clickhouse-credentials \
  --from-literal=CLICKHOUSE_HOST=clickhouse.warehouse.svc.cluster.local \
  --from-literal=CLICKHOUSE_PORT=8123 \
  --from-literal=CLICKHOUSE_USER=admin \
  --from-literal=CLICKHOUSE_PASSWORD='<senha forte>' \
  --from-literal=CLICKHOUSE_SCHEMA=dbt_demo

# Repita para grafana-admin, airflow10-stable-*, cloudflared-token
```

### Etapa 6 — Aplicar as Applications do ArgoCD

```bash
kubectl apply -f infra/src/app-manifests/deepstorage/
kubectl apply -f infra/src/app-manifests/warehouse/
kubectl apply -f infra/src/app-manifests/orchestrator/
kubectl apply -f infra/src/app-manifests/monitorability/

kubectl -n argocd get applications   # espere todos aparecerem Synced/Healthy
```

### Etapa 7 — Cloudflare Tunnel

1. No painel Cloudflare Zero Trust → **Networks** → **Tunnels** → **Create a tunnel** → escolha `cloudflared`.
2. Copie o token gerado e crie o Secret:
   ```bash
   kubectl create namespace cloudflared
   kubectl -n cloudflared create secret generic cloudflared-token \
     --from-literal=token='<TOKEN>'
   ```
3. Aplique o Deployment:
   ```bash
   kubectl apply -f infra/src/k8s-manifests/cloudflared/deployment.yaml
   ```
4. De volta ao painel, na aba **Published application routes**, adicione um registro por aplicação pública apontando para o Service interno correspondente (`airflow10-api-server.orchestrator2.svc.cluster.local:8080`, etc.).

### Etapa 8 — Cloudflare Zero Trust Access (opcional mas recomendado)

Para cada hostname público, crie uma **Application** em `Access → Applications` → *Self-hosted*, anexe uma política que use os selectors de identidade disponíveis (lista fixa de emails, domínios permitidos, grupos SSO, etc.) e habilite o provider **One-time PIN** (ou outro IdP de sua preferência). Qualquer tentativa de acesso passará primeiro pela tela de autenticação da Cloudflare antes de atingir a aplicação de fato.

Ao final, a plataforma deve estar totalmente operacional:

```bash
kubectl -n argocd get applications   # tudo Synced + Healthy
kubectl -n monitorability get pods   # grafana + prometheus Running
kubectl -n orchestrator2 get pods    # airflow10-* todos Running
kubectl -n deepstorage get pods      # datalake-pool-* Running
kubectl -n cloudflared get pods      # cloudflared conectado
```

---

## Licença e referências acadêmicas

Este projeto é parte do trabalho de conclusão do MBA em Data Science & Analytics — ICMC/USP. As versões dos charts, dashboards e scripts foram escolhidas com base em compatibilidade e estabilidade observadas durante a implementação (abril de 2026). O histórico completo de decisões e a evolução do stack estão nos commits deste repositório (`git log --oneline`).

# Avaliação de Metodologias e Técnicas para Implementação de uma Stack Moderna de Dados Open Source

> **Trabalho de Conclusão de Curso** apresentado para obtenção do título de especialista em Engenharia de Software – 2025
>
> **Aluno:** Bruno Czarnescki
> **Orientador:** Ernane José Xavier Costa

---

## Resultados Preliminares

Nesta seção, são apresentados os resultados parciais obtidos na pesquisa, conforme o cronograma estabelecido e a metodologia definida. O objetivo principal deste estudo é implementar e avaliar metodologias e técnicas relacionadas à criação de uma stack moderna open source para engenharia de dados, investigando sua aplicabilidade prática, desempenho operacional, robustez, segurança e capacidade de escala. Busca-se fornecer insights concretos que apoiem a decisão de empresas, pesquisadores e organizações na adoção de abordagens modernas, eficientes e alinhadas às melhores práticas da Engenharia de Software e Engenharia de Dados.

## Introdução e Contexto da Engenharia de Dados Moderna

O cenário atual da tecnologia é marcado por um crescimento exponencial no volume, velocidade e variedade de dados, um fenômeno conhecido como Big Data. Essa proliferação de informações impõe desafios significativos para organizações que buscam extrair valor e insights estratégicos. A engenharia de dados emerge como uma disciplina fundamental nesse contexto, focada na construção e manutenção de sistemas robustos e escaláveis para a coleta, armazenamento, processamento e disponibilização de dados para análise (Reis & Housley, 2022).

A adoção de uma stack moderna de dados, baseada em tecnologias open source, torna-se crucial para empresas e pesquisadores. Essa abordagem oferece flexibilidade, reduz custos e promove a inovação, permitindo a adaptação a diferentes necessidades e a integração com um ecossistema vasto de ferramentas e comunidades ativas (Reis & Housley, 2022). A engenharia de dados moderna requer arquiteturas robustas que integrem orquestração de pipelines, transformação de dados e armazenamento escalável, com o objetivo de "entregar valor de negócio a partir de dados em larga escala" (Reis & Housley, 2022).

Este projeto de pesquisa busca explorar um conjunto de metodologias e boas práticas para a concepção e implementação integrada de uma stack moderna e escalável de dados, baseada predominantemente em tecnologias open source. As metodologias investigadas são diretamente relacionadas às necessidades práticas do ciclo completo de dados: ingestão e orquestração (Apache Airflow), armazenamento eficiente e flexível (MinIO compatível com S3), transformação estruturada e governança dos dados (dbt), processamento analítico de alto desempenho (ClickHouse) e visualização interativa (Metabase).

## Metodologia Aplicada

A pesquisa possui caráter aplicado, sendo conduzida como um estudo de caso único em ambiente controlado, com simulação de um cenário realista de engenharia de dados. A escolha por um estudo de caso permite uma análise aprofundada de um fenômeno contemporâneo em seu contexto real, especialmente quando os limites entre o fenômeno e o contexto não são claramente evidentes (Yin, 2018).

A abordagem metodológica adotada é mista, combinando análises qualitativas com análises quantitativas. As análises qualitativas focam na avaliação da integração, facilidade de uso, aderência às boas práticas e governança das ferramentas. As análises quantitativas, por sua vez, mensuram o tempo de execução dos pipelines, o desempenho das consultas e o uso de recursos computacionais. Essa estratégia é justificada pela flexibilidade do estudo de caso em permitir a coleta e interpretação de dados diversos em contextos reais ou simulados, proporcionando uma visão holística do fenômeno analisado (Stake, 1995; Yin, 2018).

O ambiente experimental foi implementado em servidor próprio, utilizando dados sintéticos gerados com bibliotecas especializadas em Python para simular eventos e entidades de um contexto empresarial. Esta abordagem garante o isolamento do estudo e elimina riscos éticos associados ao uso de dados reais sensíveis, mantendo-se em conformidade com os requisitos da instituição. A submissão ao Comitê de Ética em Pesquisa (CEP), quando necessária, será realizada de acordo com as diretrizes institucionais, cabendo ao Comitê avaliar formalmente a exigência de aprovação após a entrega deste projeto.

Para cada etapa do ciclo de dados, foi aplicada uma metodologia compatível com a função desempenhada:

- **Orquestração de pipelines:** A plataforma Apache Airflow (Apache Software Foundation, 2023) foi utilizada para definir, programar e monitorar workflows de forma programática, por meio de DAGs (Directed Acyclic Graphs). O Airflow é amplamente reconhecido por sua capacidade de gerenciar fluxos de trabalho complexos, permitindo a automação de tarefas, o monitoramento de execuções e a recuperação de falhas, sendo uma ferramenta essencial em ambientes de engenharia de dados (Harenslak & De Ruiter, 2021).

- **Transformação e governança de dados:** A adoção do dbt (dbt Labs, 2023) permitiu aplicar práticas de engenharia de software aos pipelines analíticos, promovendo versionamento, testes automatizados e documentação das transformações SQL. O dbt facilita a construção de modelos de dados transformados, garantindo a qualidade e a consistência dos dados antes de serem consumidos para análise (dbt Labs, 2023).

- **Armazenamento de objetos:** Os dados brutos e intermediários foram armazenados no MinIO (MinIO, Inc., 2023), um sistema de armazenamento compatível com a API S3 da AWS. O MinIO é uma solução de armazenamento de objetos de alto desempenho, nativa de Kubernetes, que oferece escalabilidade e resiliência, sendo ideal para a construção de *data lakes* em ambientes de nuvem privada ou híbrida (MinIO, Inc., 2023). Sua compatibilidade com a API S3 garante a interoperabilidade com diversas ferramentas do ecossistema de dados.

- **Processamento analítico:** O banco de dados colunar ClickHouse (Schulze et al., 2024) foi utilizado como motor OLAP (Online Analytical Processing), devido à sua capacidade de executar consultas em tempo real sobre volumes massivos de dados. O ClickHouse é otimizado para cargas de trabalho analíticas, oferecendo desempenho superior em cenários que exigem agregação e filtragem rápidas de grandes conjuntos de dados (Schulze et al., 2024).

- **Visualização de dados:** A plataforma Metabase (Metabase Documentation, 2025) foi empregada para criar dashboards interativos de forma intuitiva. O Metabase é uma ferramenta de Business Intelligence (BI) de código aberto que permite a exploração de dados e a criação de visualizações de forma acessível, mesmo para usuários não técnicos, facilitando a disseminação de insights (Metabase Documentation, 2025).

## Ambiente de Execução: K3s Single-Node

Para a execução e orquestração dos componentes da stack de dados (MinIO, ClickHouse e Airflow), optou-se pela utilização de um cluster K3s (Lightweight Kubernetes) em configuração single-node. Esta escolha foi estratégica para a Prova de Conceito (PoC) acadêmica, visando maximizar o *throughput* e minimizar o *operational toil*, conforme detalhado a seguir:

- **Footprint Mínimo, Kubernetes Completo:** A documentação oficial do K3s (K3s Documentation, 2025) ressalta que uma instalação single-node server já integra todos os componentes essenciais do Kubernetes (control-plane, datastore, kubelet, containerd), estando pronta para hospedar *workload pods* sem a necessidade de agentes adicionais. Isso garante um ambiente de orquestração robusto com recursos computacionais otimizados, ideal para ambientes com recursos limitados ou para PoCs (K3s Documentation, 2025).

- **Atualizado, Certificado, Estável:** A versão v1.33.1+k3s1, a última estável, acompanha o Kubernetes v1.33.1, assegurando conformidade com a CNCF (Cloud Native Computing Foundation) e incorporando as correções mais recentes. Isso confere estabilidade e segurança ao ambiente de desenvolvimento e testes, garantindo que a PoC seja executada em uma plataforma atualizada e confiável (K3s Documentation, 2025).

- **Menor Overhead de Virtualização:** A arquitetura single-node K3s minimiza o *overhead* de virtualização em diversos aspectos, o que é crucial para otimizar o desempenho em um ambiente de PoC:
    - **CPU/RAM:** Utiliza um único *kernel*, com um só *kubelet/containerd*, otimizando o uso de recursos computacionais. Isso é particularmente vantajoso em cenários onde a alocação de recursos é um fator limitante, como em máquinas virtuais ou dispositivos de borda (K3s Documentation, 2025).
    - **Rede:** O tráfego *intra-cluster* ocorre via *loopback*, eliminando a complexidade e a latência de *vSwitch*, *virtio* e *bridge* de múltiplas VMs. Essa otimização de rede contribui diretamente para a redução da latência na comunicação entre os serviços da stack de dados, impactando positivamente o desempenho geral (K3s Documentation, 2025).
    - **Storage I/O:** Permite acesso direto ao disco-imagem, e a configuração `replica=1` no Longhorn (se utilizado) remove a duplicação de blocos, melhorando o desempenho de I/O. A eficiência no acesso ao armazenamento é vital para operações de ingestão e processamento de dados em larga escala (K3s Documentation, 2025).

- **Simplicidade Operacional / Time-to-Value:** A instalação do K3s é simplificada (*zero-touch install*), permitindo que um cluster esteja operacional em menos de 30 segundos (`curl -sfL https://get.k3s.io | sh -`). Essa agilidade, juntamente com a facilidade de atualizações, reduz significativamente a curva de entrega da PoC, permitindo que o foco principal seja no *business logic* das ferramentas (Airflow, ClickHouse, Trino, etc.). A simplicidade de implantação e gerenciamento do K3s o torna uma escolha atraente para projetos que demandam rapidez e eficiência (K3s Documentation, 2025).

- **Consistência de Benchmark:** Ao eliminar *hops* de rede e a necessidade de sincronismo entre múltiplas VMs, a variação de latência é reduzida. Isso garante maior reprodutibilidade das medições de performance, um aspecto crucial para a documentação e análise dos resultados no TCC. A consistência nos resultados de benchmark é fundamental para validar as hipóteses e conclusões da pesquisa (K3s Documentation, 2025).

- **Risco Aceitável:** Para uma PoC acadêmica, a ausência de Alta Disponibilidade (HA) e a não necessidade de expansão horizontal futura tornam o risco aceitável. Um *snapshot* do Proxmox (ambiente de virtualização subjacente) oferece cobertura para *disaster recovery*, e a adição de mais VMs acrescentaria complexidade sem benefício real de disponibilidade, visto que o *host* físico continua sendo um *single point of failure*. Em ambientes de pesquisa e desenvolvimento, a priorização da simplicidade e do desempenho sobre a alta disponibilidade é uma decisão pragmática (K3s Documentation, 2025).

Em suma, a escolha do K3s single-node para esta PoC acadêmica orientada a performance maximiza o *throughput* e minimiza o esforço operacional, justificando plenamente sua adoção no estudo.

## Gerenciamento de Infraestrutura com Argo CD

O Argo CD, uma ferramenta declarativa de GitOps para Continuous Delivery para Kubernetes, foi fundamental na implantação e gerenciamento da infraestrutura da stack de dados no cluster K3s. Através do Argo CD, os manifestos de deploy para o Airflow, MinIO e ClickHouse são versionados em um repositório Git e automaticamente sincronizados com o cluster Kubernetes. Isso garante que o estado desejado da infraestrutura seja sempre mantido, facilitando a reprodutibilidade, a auditoria e a recuperação de desastres. A abordagem GitOps, implementada com o Argo CD, promove a automação e a consistência na entrega de aplicações e serviços, reduzindo erros manuais e acelerando o ciclo de desenvolvimento (Argo CD Documentation, 2025).

## Etapas Atuais: Geração de Dados Fakes e Ingestão Inicial

Atualmente, a pesquisa encontra-se na fase de criação de dados sintéticos (*fakes*) para importação inicial no MinIO e no ClickHouse. Para isso, está sendo utilizada a biblioteca faker em Python, que permite a geração de dados realistas e diversificados, simulando cenários empresariais sem comprometer a privacidade ou a segurança de dados reais. Essa abordagem garante o isolamento do estudo e a conformidade com os requisitos éticos da instituição (Python Faker Documentation, 2025).

A geração de dados fakes é uma prática comum em projetos de engenharia de dados e testes de sistemas, pois permite simular grandes volumes de dados e diferentes padrões de comportamento sem a necessidade de acesso a dados sensíveis ou a criação manual de conjuntos de dados complexos. A biblioteca faker oferece uma ampla gama de geradores de dados, desde nomes e endereços até informações financeiras e de saúde, possibilitando a criação de dados que se assemelham a dados reais em termos de formato e distribuição (Python Faker Documentation, 2025).

Os dados gerados incluem informações que serão posteriormente utilizadas para testar os pipelines de ingestão e as capacidades de armazenamento e processamento das ferramentas. A ingestão inicial desses dados no MinIO (como *data lake* para dados brutos) e no ClickHouse (para processamento analítico) é um passo fundamental para validar a conectividade e o fluxo de dados entre os componentes da stack. Esta etapa é crucial para garantir que as ferramentas estejam configuradas corretamente e que a comunicação entre elas esteja funcionando conforme o esperado, antes de avançar para as etapas de transformação e análise.

## Próximos Passos: Construção do Projeto dbt

Após a finalização da etapa de ingestão inicial dos dados *fakes* e a validação da conectividade entre MinIO, ClickHouse e Airflow, o próximo passo crucial será a construção do projeto dbt (Data Build Tool). Atualmente, o dbt encontra-se em modo de espera, aguardando a finalização da arquitetura de ingestão e a consolidação dos dados brutos. Uma vez que a base de dados esteja estabelecida e os pipelines de ingestão estejam operacionais, o dbt será criado e aplicado no projeto, sendo posteriormente linkado ao Apache Airflow para orquestração das transformações. O dbt será responsável por aplicar as transformações e a governança sobre os dados brutos armazenados no MinIO, criando modelos de dados estruturados e otimizados para análise no ClickHouse. Este processo incluirá:

- **Definição de Modelos:** Criação de modelos SQL no dbt para transformar os dados brutos em formatos mais consumíveis, aplicando regras de negócio e garantindo a qualidade dos dados. Os modelos dbt são escritos em SQL e podem ser versionados, testados e documentados, o que promove a colaboração e a manutenibilidade do código (dbt Labs, 2023).

- **Testes Automatizados:** Implementação de testes de integridade e qualidade de dados no dbt para assegurar que as transformações ocorram sem erros e que os dados resultantes sejam consistentes. Os testes dbt podem verificar a unicidade de chaves, a não nulidade de colunas, a validade de valores e outras regras de negócio, garantindo a confiabilidade dos dados (dbt Labs, 2023).

- **Documentação:** Geração automática de documentação do projeto dbt, facilitando a compreensão da linhagem dos dados e das lógicas de transformação. A documentação dbt inclui descrições de modelos, colunas, testes e dependências, tornando o projeto mais transparente e fácil de ser compreendido por outros membros da equipe (dbt Labs, 2023).

- **Versionamento:** Utilização do controle de versão para o código dbt, permitindo o rastreamento de alterações e a colaboração no desenvolvimento dos modelos de dados. A integração com sistemas de controle de versão como o Git é uma prática recomendada em projetos de engenharia de dados, garantindo a rastreabilidade e a capacidade de reverter alterações.

O projeto dbt será integrado aos pipelines orquestrados pelo Apache Airflow, garantindo que as transformações de dados sejam executadas de forma automatizada e programada, como parte do fluxo completo de engenharia de dados. Essa integração permite que as transformações de dados sejam acionadas após a ingestão dos dados brutos, garantindo que os dados estejam sempre atualizados e prontos para análise.

## Repositório do Projeto

Todo o desenvolvimento e os artefatos relacionados a este projeto de TCC estão disponíveis publicamente no repositório GitHub do aluno: <https://github.com/brunocza/mba_usp-data_stack>. Este repositório serve como uma fonte de referência para o código-fonte, configurações e exemplos utilizados na implementação da stack de dados, promovendo a transparência e a reprodutibilidade da pesquisa.

## Conclusão

Os resultados preliminares apresentados neste trabalho demonstram o progresso significativo na implementação de uma stack moderna de engenharia de dados baseada em tecnologias open source. A escolha do K3s em configuração single-node para orquestração da infraestrutura provou ser uma abordagem eficiente para a Prova de Conceito, otimizando o uso de recursos e simplificando a gestão do ambiente. A utilização do Argo CD para o deploy da infraestrutura no K3s e a sincronização dos repositórios de DAGs do Airflow reforçam a adoção de práticas de GitOps, garantindo automação, consistência e reprodutibilidade do ambiente.

A implementação e operação do Apache Airflow, MinIO e ClickHouse, conforme detalhado, estabelecem a base para as próximas etapas da pesquisa. A fase atual de geração de dados sintéticos com a biblioteca faker em Python é crucial para a validação do fluxo de dados e a conectividade entre os componentes da stack, permitindo testes em um ambiente controlado e ético. Essa abordagem assegura que a ingestão inicial de dados no MinIO e ClickHouse seja robusta e funcional, preparando o terreno para as transformações de dados.

O projeto dbt, embora em modo de espera, representa o próximo passo fundamental na arquitetura proposta. Sua integração futura com o Apache Airflow permitirá a aplicação de práticas de engenharia de software às transformações de dados, promovendo a qualidade, governança e documentação dos modelos de dados. A expectativa é que, com a conclusão da arquitetura de ingestão e a aplicação do dbt, a stack de dados atinja um nível de maturidade que permita análises mais aprofundadas e a validação das hipóteses iniciais do estudo. O repositório GitHub do projeto continuará a ser atualizado, refletindo o progresso e os artefatos desenvolvidos, contribuindo para a transparência e a reprodutibilidade da pesquisa.

## Referências

APACHE SOFTWARE FOUNDATION. 2023. *Apache Airflow Documentation* (v2.5). Apache Software Foundation, Wilmington, DE, EUA. Disponível em: <https://airflow.apache.org/docs/apache-airflow/stable/>. Acesso em: 17 jun. 2025.

ARGO CD. 2025. *Argo CD Documentation*. Disponível em: <https://argo-cd.readthedocs.io/en/stable/>. Acesso em: 17 jun. 2025.

DBT LABS. 2023. *dbt Documentation: What is dbt?*. dbt Labs, Philadelphia, PA, EUA. Disponível em: <https://docs.getdbt.com/docs/introduction>. Acesso em: 17 jun. 2025.

HARENSLAK, Bas; DE RUITER, Julian. 2021. *Data Pipelines with Apache Airflow*. Manning Publications, Shelter Island, NY, EUA.

K3S DOCUMENTATION. 2025. *K3s: Lightweight Kubernetes*. Disponível em: <https://k3s.io/>. Acesso em: 17 jun. 2025.

METABASE DOCUMENTATION. 2025. *Metabase: The open source analytics and business intelligence platform*. Disponível em: <https://www.metabase.com/docs/>. Acesso em: 17 jun. 2025.

MinIO, Inc. 2023. *MinIO Object Storage Documentation*. MinIO, Inc., Redwood City, CA, EUA. Disponível em: <https://min.io/docs/minio/linux/>. Acesso em: 17 jun. 2025.

PYTHON FAKER DOCUMENTATION. 2025. *Faker: A Python package to generate fake data*. Disponível em: <https://faker.readthedocs.io/en/master/>. Acesso em: 17 jun. 2025.

REIS, Joe; HOUSLEY, Matt. 2022. *Fundamentals of Data Engineering: Plan and Build Robust Data Systems*. 1ª ed. O'Reilly Media, Sebastopol, CA, EUA.

SCHULZE, Robert; SCHREIBER, Tom; YATSISHIN, Ilya; DAHIMENE, Ryadh; MILOVIDOV, Alexey. 2024. *ClickHouse – Lightning Fast Analytics for Everyone*. Proceedings of the VLDB Endowment (PVLDB), 17(12): 3731–3744.

STAKE, Robert E. 1995. *The Art of Case Study Research*. Sage Publications, Thousand Oaks, CA, EUA.

YIN, Robert K. 2018. *Case Study Research and Applications: Design and Methods*. 6ª ed. Sage Publications, Thousand Oaks, CA, EUA.

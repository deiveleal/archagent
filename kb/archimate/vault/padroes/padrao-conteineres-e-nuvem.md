---
id: padrao-conteineres-e-nuvem
tipo: padrao
camada: tecnologia
tags: [kubernetes, nuvem, conteiner]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Aplicações em contêineres e nuvem

**Quando usar:** a entrada cita Kubernetes, Docker ou um provedor de nuvem.

**Forma:**

- O cluster ou a conta de nuvem vira [[elemento-node]].
- Kubernetes, Docker e bancos gerenciados viram [[elemento-system-software]] ou [[elemento-technology-service]].
- A imagem do contêiner vira [[elemento-artifact]], que realiza o [[elemento-application-component]] e é atribuída ao nó.
- A rede (VPC, sub-rede) vira [[elemento-communication-network]].

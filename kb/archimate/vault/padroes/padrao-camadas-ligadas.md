---
id: padrao-camadas-ligadas
tipo: padrao
camada: todas
tags: [camadas, servico]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Camadas ligadas por serviços

**Quando usar:** sempre que o modelo tiver mais de uma camada.

**Forma:** cada camada serve a de cima por meio de serviços.

- Tecnologia → Aplicação: [[elemento-system-software]] ou [[elemento-node]] servem (Serving) o [[elemento-application-component]], ou realizam um [[elemento-technology-service]] que o serve.
- Aplicação → Negócio: o [[elemento-application-component]] realiza (Realization) um [[elemento-application-service]], que serve (Serving) o [[elemento-business-process]].
- Negócio: o [[elemento-business-actor]] é atribuído (Assignment) ao processo.

**Por quê:** é o que os critérios COE-04 a COE-08 verificam.

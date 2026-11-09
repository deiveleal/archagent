---
id: padrao-integracao-por-api
tipo: padrao
camada: aplicacao
tags: [integracao, api]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Integração entre sistemas por API

**Quando usar:** um sistema chama outro por API, fila ou arquivo.

**Forma:**

- O sistema chamado tem uma [[elemento-application-interface]] (ex.: "REST /pedidos") que compõe o seu [[elemento-application-component]].
- O sistema chamado oferece um [[elemento-application-service]] que serve (Serving) o sistema que chama.
- Quando o foco é a passagem de dados, use Flow de um componente para o outro, com o nome do dado.

**Dica:** prefira Serving para dependência e Flow para troca de informação; não use as duas para a mesma ligação.

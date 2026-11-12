---
id: convencao-nomes
tipo: convencao
camada: todas
tags: [nomes, idioma]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Nomes dos elementos

- Nomes em **português do Brasil**, como aparecem na entrada; nomes próprios de produtos ficam como são ("PostgreSQL").
- Processos ([[elemento-business-process]], [[elemento-application-process]], [[elemento-technology-process]]): **verbo no infinitivo + objeto** ("Registrar pedido").
- Eventos: fato no particípio ("Pedido recebido").
- Serviços: substantivo de ação + objeto, do ponto de vista de quem usa ("Consulta de pedido", "Pagamento online"); não repetir o nome do processo que o realiza.
- Funções: área de atuação ou competência ("Gestão de clientes", "Faturamento").
- Estruturas e dados: substantivo no singular ("Cliente", "Pedido").
- No máximo 60 caracteres; detalhes vão na documentação do elemento.
- Nomes únicos por tipo (regra COE-03).

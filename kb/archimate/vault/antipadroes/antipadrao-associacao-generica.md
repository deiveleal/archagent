---
id: antipadrao-associacao-generica
tipo: antipadrao
camada: todas
tags: [relacao, association]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Association para tudo

**Sinal:** muitas relações Association onde caberia uma relação com significado.

**Problema:** Association não diz nada sobre dependência, responsabilidade ou fluxo.

**Correção:** prefira Serving (quem serve quem), Realization (quem realiza o serviço), Assignment (quem executa), Access (quem usa o dado), Flow (troca de informação) e Triggering (ordem). Use Association só quando nenhuma delas couber. Ver [[convencao-escolha-de-relacoes]].

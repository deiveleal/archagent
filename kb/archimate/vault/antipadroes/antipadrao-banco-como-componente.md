---
id: antipadrao-banco-como-componente
tipo: antipadrao
camada: aplicacao
tags: [banco, dados]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Banco de dados como componente de aplicação

**Sinal:** "PostgreSQL" ou "Banco Oracle" como [[elemento-application-component]].

**Problema:** o banco é software de base, não software do negócio.

**Correção:** o produto vira [[elemento-system-software]]; os dados viram [[elemento-data-object]]. Ver [[padrao-banco-de-dados]].

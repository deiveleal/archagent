---
id: elemento-data-object
tipo: elemento
archimate: DataObject
camada: aplicacao
tags: [estrutura-passiva, dados, entidade, tabela]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Objeto de dados (DataObject)

**Definição (com nossas palavras):** Dados estruturados usados pelo software: uma entidade, um documento JSON, uma tabela.

**Use quando:** a entrada cita entidades, tabelas, mensagens ou documentos de dados num sistema.

**Não use quando:** é o conceito do negócio (use [[elemento-business-object]]); é o banco como produto (use [[elemento-system-software]]); é o arquivo físico (use [[elemento-artifact]]).

**Confusões comuns:** Objeto de dados × Banco: 'Pedido' é dado; 'PostgreSQL' é software de sistema.

**Como nomear:** substantivo no singular. Ex.: "Pedido", "Cadastro de cliente".

**Relações típicas:** é acessado por [[elemento-application-component]] e [[elemento-application-function]]; realiza [[elemento-business-object]]; é realizado por [[elemento-artifact]].

**Exemplo:** "Pedido" escrito pela "API de Pedidos".

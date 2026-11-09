---
id: elemento-business-role
tipo: elemento
archimate: BusinessRole
camada: negocio
tags: [estrutura-ativa, responsabilidade]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Papel de negócio (BusinessRole)

**Definição (com nossas palavras):** Uma responsabilidade que alguém assume no negócio, como 'aprovador' ou 'atendente'. Vários atores podem exercer o mesmo papel.

**Use quando:** a entrada descreve funções que pessoas diferentes podem ocupar, ou separa quem é de o que faz.

**Não use quando:** há uma pessoa ou área concreta e o papel não acrescenta nada (use [[elemento-business-actor]]).

**Confusões comuns:** Papel × Ator (ver [[elemento-business-actor]]). Papel × Função: papel é quem faz; função é o que é feito.

**Como nomear:** substantivo que indica a responsabilidade. Ex.: "Aprovador de crédito".

**Relações típicas:** recebe Assignment de [[elemento-business-actor]]; é atribuído a [[elemento-business-process]] e [[elemento-business-function]].

**Exemplo:** "Atendente" atribuído a "Abrir chamado".

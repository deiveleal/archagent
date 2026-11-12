---
id: elemento-business-interface
tipo: elemento
archimate: BusinessInterface
camada: negocio
tags: [estrutura-ativa, canal, atendimento]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Interface de negócio (BusinessInterface)

**Definição (com nossas palavras):** Um canal pelo qual o negócio oferece os seus serviços: balcão, telefone, e-mail, portal visto do lado do negócio.

**Use quando:** a entrada cita canais de atendimento ou pontos de contato com clientes e parceiros.

**Não use quando:** é uma tela ou API de software (use [[elemento-application-interface]]).

**Confusões comuns:** Interface de negócio × de aplicação: a de negócio é o canal; a de aplicação é o ponto técnico.

**Como nomear:** substantivo do canal. Ex.: "Central de atendimento".

**Relações típicas:** faz parte (Composition) de [[elemento-business-actor]] ou [[elemento-business-role]]; disponibiliza [[elemento-business-service]] (Assignment).

**Exemplo:** "Central telefônica" do papel "Atendente".

---
id: elemento-application-interaction
tipo: elemento
archimate: ApplicationInteraction
camada: aplicacao
tags: [comportamento, integracao]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Interação de aplicação (ApplicationInteraction)

**Definição (com nossas palavras):** Um comportamento feito em conjunto por dois ou mais componentes.

**Use quando:** a entrada descreve uma troca entre sistemas que só existe com as duas partes.

**Não use quando:** um componente executa sozinho (use [[elemento-application-function]]).

**Confusões comuns:** Interação × Flow: Flow só mostra a passagem de informação.

**Como nomear:** verbo no infinitivo. Ex.: "Sincronizar clientes".

**Relações típicas:** recebe Assignment de [[elemento-application-collaboration]].

**Exemplo:** "Sincronizar estoque" da colaboração "Integração loja–ERP".

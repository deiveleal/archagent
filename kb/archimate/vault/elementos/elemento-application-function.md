---
id: elemento-application-function
tipo: elemento
archimate: ApplicationFunction
camada: aplicacao
tags: [comportamento, funcionalidade]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Função de aplicação (ApplicationFunction)

**Definição (com nossas palavras):** Um comportamento interno de um componente, agrupado por funcionalidade, sem sequência.

**Use quando:** a entrada detalha o que um sistema faz por dentro, como 'cálculo de frete'.

**Não use quando:** o que importa é o que é oferecido para fora (use [[elemento-application-service]]).

**Confusões comuns:** Função × Serviço: a função é interna; o serviço é a parte visível.

**Como nomear:** substantivo de atividade ou verbo. Ex.: "Cálculo de frete".

**Relações típicas:** recebe Assignment de [[elemento-application-component]]; realiza [[elemento-application-service]]; acessa [[elemento-data-object]].

**Exemplo:** "Cálculo de frete" do componente "Logística".

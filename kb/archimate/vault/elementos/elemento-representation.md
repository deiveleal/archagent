---
id: elemento-representation
tipo: elemento
archimate: Representation
camada: negocio
tags: [estrutura-passiva, documento, formulario]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Representação (Representation)

**Definição (com nossas palavras):** A forma perceptível de uma informação de negócio: formulário, relatório impresso, mensagem.

**Use quando:** a entrada cita um formulário, relatório ou documento físico que leva a informação.

**Não use quando:** importa o conceito e não a forma (use [[elemento-business-object]]).

**Confusões comuns:** Representação × Artefato: representação é a forma vista pelo negócio; artefato é o arquivo técnico.

**Como nomear:** substantivo da forma. Ex.: "Formulário de pedido".

**Relações típicas:** realiza [[elemento-business-object]].

**Exemplo:** "Nota fiscal impressa" realiza "Nota fiscal".

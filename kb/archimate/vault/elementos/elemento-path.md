---
id: elemento-path
tipo: elemento
archimate: Path
camada: tecnologia
tags: [estrutura-ativa, comunicacao, link]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Caminho (Path)

**Definição (com nossas palavras):** Uma ligação lógica de comunicação entre nós, sem detalhar a rede física.

**Use quando:** a entrada diz que dois servidores se comunicam, sem detalhar a rede.

**Não use quando:** é a rede física ou de infraestrutura (use [[elemento-communication-network]]).

**Confusões comuns:** Caminho × Rede: caminho é a ligação lógica; rede é o meio.

**Como nomear:** substantivo. Ex.: "Ligação app–banco".

**Relações típicas:** liga [[elemento-node]] por Association; é realizado por [[elemento-communication-network]].

**Exemplo:** "VPN matriz–filial".

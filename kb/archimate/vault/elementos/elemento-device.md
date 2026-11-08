---
id: elemento-device
tipo: elemento
archimate: Device
camada: tecnologia
tags: [estrutura-ativa, hardware, equipamento]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Dispositivo (Device)

**Definição (com nossas palavras):** Um equipamento físico com capacidade de processamento: celular, terminal, impressora, sensor.

**Use quando:** a entrada cita aparelhos físicos, como celulares, totens ou leitores.

**Não use quando:** é um servidor virtual ou nuvem (use [[elemento-node]]).

**Confusões comuns:** Dispositivo é um tipo especial de nó, para hardware.

**Como nomear:** substantivo do equipamento. Ex.: "Celular do entregador".

**Relações típicas:** compõe [[elemento-node]]; recebe [[elemento-system-software]] (Assignment); serve [[elemento-application-component]].

**Exemplo:** "Totem de autoatendimento" rodando o app de pedidos.

---
id: elemento-communication-network
tipo: elemento
archimate: CommunicationNetwork
camada: tecnologia
tags: [estrutura-ativa, rede, vpc, lan]
fontes:
  - "ArchiMate 3.2, cap. 10 (Camada de Tecnologia)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Rede de comunicação (CommunicationNetwork)

**Definição (com nossas palavras):** Uma rede que liga nós e transmite dados: LAN, VPC, internet, VPN.

**Use quando:** a entrada cita rede, VPC, sub-rede, internet ou VPN.

**Não use quando:** é só uma ligação lógica (use [[elemento-path]]).

**Confusões comuns:** Rede × Caminho (ver [[elemento-path]]).

**Como nomear:** substantivo. Ex.: "VPC de produção".

**Relações típicas:** liga [[elemento-node]] e [[elemento-device]] por Association; realiza [[elemento-path]].

**Exemplo:** "VPC de produção" ligando o cluster e o banco.

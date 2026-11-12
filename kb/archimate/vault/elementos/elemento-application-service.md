---
id: elemento-application-service
tipo: elemento
archimate: ApplicationService
camada: aplicacao
tags: [comportamento, servico, funcionalidade-exposta]
fontes:
  - "ArchiMate 3.2, cap. 9 (Camada de Aplicação)"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Serviço de aplicação (ApplicationService)

**Definição (com nossas palavras):** Uma funcionalidade que o software expõe para pessoas ou outros sistemas, descrita pelo que entrega.

**Use quando:** a entrada fala do que um sistema oferece: 'consulta de pedidos', 'emissão de boleto'. Só crie o serviço quando a entrada o cita; senão, o componente serve o processo diretamente (ver [[padrao-camadas-ligadas]]).

**Não use quando:** é o software em si (use [[elemento-application-component]]); é o ponto técnico de acesso (use [[elemento-application-interface]]).

**Confusões comuns:** Serviço × Componente (ver [[elemento-application-component]]).

**Como nomear:** substantivo de ação + objeto, do ponto de vista de quem usa. Ex.: "Consulta de pedidos".

**Relações típicas:** é realizado por [[elemento-application-component]], [[elemento-application-function]] ou [[elemento-application-process]]; serve [[elemento-business-process]] e outros componentes.

**Exemplo:** "Emissão de boleto" realizado por "Financeiro" e servindo "Cobrar cliente".

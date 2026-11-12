---
id: padrao-camadas-ligadas
tipo: padrao
camada: todas
tags: [camadas, servico]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: revisado
revisado_por: "Deive Leal"
revisado_em: 2026-11-12
---

# Camadas ligadas por serviços

**Quando usar:** sempre que o modelo tiver mais de uma camada.

**Forma simples (padrão do MVP):** ligue as camadas diretamente, sem inventar elementos.

- Tecnologia → Aplicação: [[elemento-system-software]], [[elemento-node]] ou [[elemento-device]] servem (Serving) o [[elemento-application-component]].
- Aplicação → Negócio: o [[elemento-application-component]] serve (Serving) o [[elemento-business-process]].
- Negócio: o [[elemento-business-actor]] é atribuído (Assignment) ao processo. Quando a entrada cita um cargo ou papel ("o atendente", "o gestor de frota"), use ator → [[elemento-business-role]] → processo, ambos por Assignment.

**Forma detalhada (só quando a entrada cita os serviços):** o componente realiza (Realization) um [[elemento-application-service]], que serve o processo; a tecnologia realiza um [[elemento-technology-service]], que serve o componente. Pelas regras de derivação do ArchiMate, as duas formas são equivalentes.

**Por quê:** é o que os critérios COE-05, COE-07 e COE-08 verificam; inventar serviços aumenta as premissas sem trazer informação da entrada.

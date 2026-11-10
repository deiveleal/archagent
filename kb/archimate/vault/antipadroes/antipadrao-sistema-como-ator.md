---
id: antipadrao-sistema-como-ator
tipo: antipadrao
camada: negocio
tags: [ator, sistema]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Sistema modelado como ator de negócio

**Sinal:** um [[elemento-business-actor]] com nome de sistema ("ERP", "Portal").

**Problema:** atores de negócio são pessoas ou organizações. O sistema é software.

**Correção:** use [[elemento-application-component]] para o sistema e ligue-o ao negócio por Serving; um [[elemento-application-service]] intermediário só entra quando a entrada o cita (ver [[padrao-camadas-ligadas]]).

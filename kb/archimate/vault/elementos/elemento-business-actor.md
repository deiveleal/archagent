---
id: elemento-business-actor
tipo: elemento
archimate: BusinessActor
camada: negocio
tags: [estrutura-ativa, pessoa, organizacao, area]
fontes:
  - "ArchiMate 3.2, cap. 8 (Camada de Negócio)"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Ator de negócio (BusinessActor)

**Definição (com nossas palavras):** Uma pessoa, área, empresa ou outra organização que age no negócio. É quem existe de fato, independente do que faz.

**Use quando:** a entrada cita um cliente, um fornecedor, um departamento, uma equipe ou uma empresa parceira.

**Não use quando:** o que importa é a responsabilidade e não quem a exerce (use [[elemento-business-role]]); quando é um sistema (use [[elemento-application-component]]).

**Confusões comuns:** Ator × Papel: 'Maria' ou 'Financeiro' é ator; 'Aprovador de pedidos' é papel. Sistemas nunca são atores de negócio.

**Como nomear:** substantivo no singular, nome da pessoa, área ou organização. Ex.: "Cliente", "Área Financeira".

**Relações típicas:** é atribuído (Assignment) a [[elemento-business-role]] ou diretamente a [[elemento-business-process]]; usa [[elemento-business-interface]].

**Exemplo:** "Cliente" atribuído ao processo "Registrar pedido".

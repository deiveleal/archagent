---
id: padrao-banco-de-dados
tipo: padrao
camada: todas
tags: [dados, banco]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Dados guardados em banco

**Quando usar:** a entrada diz que um sistema grava ou lê dados num banco.

**Forma:**

- Os dados viram [[elemento-data-object]] (ex.: "Pedido"), acessados (Access, com Read/Write) pelo [[elemento-application-component]].
- O banco como produto vira [[elemento-system-software]] (ex.: "PostgreSQL"), que serve o componente.
- Se a entrada citar onde o banco roda, ele fica num [[elemento-node]].

**Evite:** modelar o banco como componente de aplicação (ver [[antipadrao-banco-como-componente]]).

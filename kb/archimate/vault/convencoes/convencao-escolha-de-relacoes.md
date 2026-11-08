---
id: convencao-escolha-de-relacoes
tipo: convencao
camada: todas
tags: [relacoes]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Escolha da relação

| Situação | Relação |
| --- | --- |
| A oferece algo que B usa | Serving (A → B) |
| A implementa o serviço B | Realization (A → B) |
| A executa ou é responsável por B | Assignment (A → B) |
| A lê ou grava o dado B | Access (A → B), com Read, Write ou ReadWrite |
| Informação passa de A para B | Flow (A → B) |
| A acontece antes de B e o dispara | Triggering (A → B) |
| B é parte de A e não existe sem A | Composition (A → B) |
| B é parte de A, mas existe sozinho | Aggregation (A → B) |
| Nenhuma das anteriores | Association |

A ferramenta de relações permitidas confere se a relação vale para os dois tipos. Ver [[antipadrao-associacao-generica]].

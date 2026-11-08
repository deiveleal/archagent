---
id: convencao-origem-e-premissa
tipo: convencao
camada: todas
tags: [rastreabilidade]
fontes:
  - "ArchiMate 3.2"
  - "ArchiMate Cookbook"
status: rascunho
revisado_por: null
revisado_em: null
---

# Origem e premissa

- Todo elemento e toda relação citam os itens do briefing de onde vieram (propriedade `archagent:origem`).
- Um elemento sem origem direta só entra como **premissa** (`archagent:premissa = sim`), com o motivo na documentação.
- Itens de briefing do tipo `hipotese` ou `pendencia` só viram elementos como premissa.

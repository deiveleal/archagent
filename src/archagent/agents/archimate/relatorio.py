"""Relatório de viabilidade em Markdown (spec §11)."""

from __future__ import annotations

from collections import Counter

from archagent.agents.archimate.model import Achado, Modelo
from archagent.agents.archimate.rules import Regras
from archagent.core.briefing import Briefing, Pergunta
from archagent.core.sessions import Entrada, Uso

CRITERIOS = {
    "V1": "Formato (XSD do Exchange Format)",
    "V2": "ArchiMate 3.2 (tipos e relações)",
    "V3": "Coerência",
    "V4": "Cobertura da entrada",
    "V5": "Abre no Archi",
}
CAMADAS = {"negocio": "Negócio", "aplicacao": "Aplicação", "tecnologia": "Tecnologia"}


def _esc(t: str) -> str:
    return t.replace("|", "\\|").replace("\n", " ")


def _achados(lista: list[Achado]) -> list[str]:
    return [f"- **{a.criterio} {a.regra}**: {_esc(a.mensagem)}" for a in lista]


def gerar_relatorio(
    m: Modelo,
    regras: Regras,
    briefing: Briefing,
    entradas: list[Entrada],
    perguntas: list[Pergunta],
    uso: Uso,
    segundos: float,
    rodadas: int,
) -> str:
    v = m.validacao
    por_camada: Counter[str] = Counter(regras.camada(e.tipo) or "?" for e in m.elementos)
    rel_camada: Counter[str] = Counter(
        regras.camada(e.tipo) or "?" for r in m.relacoes if (e := m.elemento(r.origem)) is not None
    )
    nomes = {e.id: e for e in m.elementos}
    out: list[str] = [f"# Relatório de viabilidade — {m.nome} ({m.id})", ""]

    # 1. Resumo
    out += [
        "## 1. Resumo",
        "",
        f"**{'Viável' if v.viavel else 'Não viável'}** — {len(m.elementos)} elementos, "
        f"{len(m.relacoes)} relações, {len(m.visoes)} visões, {rodadas} rodada(s) de "
        "correção.",
        "",
        "| Camada | Elementos | Relações (pela origem) |",
        "| --- | --- | --- |",
    ]
    for c, rot in CAMADAS.items():
        out.append(f"| {rot} | {por_camada.get(c, 0)} | {rel_camada.get(c, 0)} |")
    out += [
        "",
        "Visões: "
        + (
            ", ".join(f"{x.nome} ({x.viewpoint}, {len(x.nos)} elementos)" for x in m.visoes)
            or "nenhuma"
        ),
        "",
    ]

    # 2. Entradas
    out += ["## 2. Entradas usadas", ""]
    out += [
        f"- {e.id} — {e.nome_arquivo or 'mensagem'} ({e.tipo}, {e.formato})"
        for e in entradas
        if e.status == "interpretada"
    ]
    fora = [e for e in entradas if e.status != "interpretada"]
    if fora:
        out += ["", "Não usadas:", ""]
        out += [
            f"- {e.id} — {e.nome_arquivo or 'mensagem'} ({e.status}"
            f"{': ' + e.observacao if e.observacao else ''})"
            for e in fora
        ]
    out.append("")

    # 3. Validação
    out += ["## 3. Resultado da validação", "", "| Critério | Resultado |", "| --- | --- |"]
    for c, rot in CRITERIOS.items():
        ok = v.criterios.get(c)
        out.append(f"| {c} — {rot} | {'ok' if ok else ('falhou' if ok is False else '—')} |")
    out.append("")
    if v.erros:
        out += ["**Erros:**", "", *_achados(v.erros), ""]
    if v.avisos:
        out += ["**Avisos:**", "", *_achados(v.avisos), ""]

    # 4. Rastreabilidade
    out += [
        "## 4. Rastreabilidade",
        "",
        "| Item do briefing | Elementos | Relações |",
        "| --- | --- | --- |",
    ]
    for i in briefing.ativos():
        if i.tipo == "conflito":
            continue
        els = [f"{e.nome} ({e.tipo})" for e in m.elementos if i.id in e.origens]
        rels = [
            f"{nomes[r.origem].nome if r.origem in nomes else '?'} —{r.tipo}→ "
            f"{nomes[r.destino].nome if r.destino in nomes else '?'}"
            for r in m.relacoes
            if i.id in r.origens
        ]
        out.append(
            f"| {i.id} {_esc(i.nome)} ({i.tipo}) | {_esc('; '.join(els)) or '—'} | "
            f"{_esc('; '.join(rels)) or '—'} |"
        )
    out.append("")

    # 5. Premissas
    premissas = [e for e in m.elementos if e.premissa]
    out += ["## 5. Premissas", ""]
    out += [
        f"- {e.nome} ({e.tipo}): {_esc(e.motivo_premissa or 'sem motivo informado')}"
        for e in premissas
    ] or ["Nenhuma."]
    out.append("")

    # 6. Pendências e conflitos
    abertos = [
        i
        for i in briefing.ativos()
        if i.tipo in ("pendencia", "conflito") or i.confianca == "baixa"
    ]
    puladas = [p for p in perguntas if p.status in ("pulada", "pendente")]
    out += ["## 6. Pendências e conflitos abertos", ""]
    out += [
        f"- {i.id} ({i.tipo}, confiança {i.confianca}): {_esc(i.nome)}"
        f"{' — ' + _esc(i.descricao) if i.descricao else ''}"
        for i in abertos
    ]
    out += [f"- Pergunta {p.id} sobre {p.item} ({p.status}): {_esc(p.texto)}" for p in puladas]
    if not abertos and not puladas:
        out.append("Nenhum.")
    out.append("")

    # 7. Superados
    superados = [i for i in briefing.itens if i.status == "superado"]
    out += ["## 7. Itens superados", ""]
    out += [f"- {i.id} {_esc(i.nome)} → {i.superado_por}" for i in superados] or ["Nenhum."]
    out.append("")

    # 8. Consumo
    out += [
        "## 8. Consumo",
        "",
        f"- Tokens da sessão: {uso.total} em {uso.chamadas} chamadas",
        *[f"  - {no}: {t}" for no, t in sorted(uso.por_no.items())],
        f"- Tempo de geração do modelo: {segundos:.0f} s",
        "",
    ]
    return "\n".join(out)

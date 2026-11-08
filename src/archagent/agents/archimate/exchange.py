"""Exportação para o Open Group ArchiMate Exchange Format e validação V1 (spec §4.7)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from lxml import etree

from archagent.agents.archimate.model import Achado, Modelo, Visao, novo_id

NS = "http://www.opengroup.org/xsd/archimate/3.0/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
XML_NS = "http://www.w3.org/XML/1998/namespace"
SCHEMA_LOCATION = f"{NS} http://www.opengroup.org/xsd/archimate/3.1/archimate3_Diagram.xsd"
LANG = "pt-BR"

PROP_ORIGEM = "propid-archagent-origem"
PROP_PREMISSA = "propid-archagent-premissa"


def _q(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def _texto(pai: etree._Element, tag: str, valor: str) -> etree._Element:
    el = etree.SubElement(pai, _q(tag))
    el.set(f"{{{XML_NS}}}lang", LANG)
    el.text = valor
    return el


def _propriedades(pai: etree._Element, origens: list[str], premissa: bool) -> None:
    props = etree.SubElement(pai, _q("properties"))
    for ref, valor in (
        (PROP_ORIGEM, ", ".join(origens)),
        (PROP_PREMISSA, "sim" if premissa else "nao"),
    ):
        p = etree.SubElement(props, _q("property"), propertyDefinitionRef=ref)
        _texto(p, "value", valor or "-")


def exportar(m: Modelo) -> bytes:
    """Gera o Exchange Format (modelo + visões)."""
    nsmap: Any = {None: NS, "xsi": XSI}
    raiz = etree.Element(_q("model"), nsmap=nsmap)
    raiz.set(f"{{{XSI}}}schemaLocation", SCHEMA_LOCATION)
    raiz.set("identifier", m.exchange_id)
    _texto(raiz, "name", m.nome)

    if m.elementos:
        elementos = etree.SubElement(raiz, _q("elements"))
        for e in m.elementos:
            el = etree.SubElement(elementos, _q("element"), identifier=e.id)
            el.set(f"{{{XSI}}}type", e.tipo)
            _texto(el, "name", e.nome)
            doc = e.documentacao
            if e.premissa and e.motivo_premissa:
                doc = f"{doc}\n\nPremissa: {e.motivo_premissa}".strip()
            if doc:
                _texto(el, "documentation", doc)
            _propriedades(el, e.origens, e.premissa)

    if m.relacoes:
        relacoes = etree.SubElement(raiz, _q("relationships"))
        for r in m.relacoes:
            el = etree.SubElement(relacoes, _q("relationship"), identifier=r.id,
                                  source=r.origem, target=r.destino)  # fmt: skip
            el.set(f"{{{XSI}}}type", r.tipo)
            if r.tipo == "Access" and r.acesso:
                el.set("accessType", r.acesso)
            if r.nome:
                _texto(el, "name", r.nome)
            _propriedades(el, r.origens, r.premissa)

    defs = etree.SubElement(raiz, _q("propertyDefinitions"))
    for ident, nome in ((PROP_ORIGEM, "archagent:origem"), (PROP_PREMISSA, "archagent:premissa")):
        d = etree.SubElement(defs, _q("propertyDefinition"), identifier=ident, type="string")
        _texto(d, "name", nome)

    if m.visoes:
        diagramas = etree.SubElement(etree.SubElement(raiz, _q("views")), _q("diagrams"))
        for v in m.visoes:
            _visao(diagramas, v, m)

    return bytes(etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", pretty_print=True))


def _visao(pai: etree._Element, v: Visao, m: Modelo) -> None:
    view = etree.SubElement(pai, _q("view"), identifier=v.id, viewpoint=v.viewpoint)
    view.set(f"{{{XSI}}}type", "Diagram")
    _texto(view, "name", v.nome)
    no_por_elemento: dict[str, str] = {}

    def no_elemento(destino: etree._Element, eid: str, x: int, y: int, w: int, h: int) -> None:
        nid = novo_id()
        no_por_elemento[eid] = nid
        n = etree.SubElement(destino, _q("node"), identifier=nid, elementRef=eid,
                             x=str(x), y=str(y), w=str(w), h=str(h))  # fmt: skip
        n.set(f"{{{XSI}}}type", "Element")

    restantes = list(v.nos)
    for f in v.faixas:
        c = etree.SubElement(view, _q("node"), identifier=novo_id(), x=str(f.x), y=str(f.y),
                             w=str(f.w), h=str(f.h))  # fmt: skip
        c.set(f"{{{XSI}}}type", "Container")
        _texto(c, "label", f.rotulo)
        dentro = [n for n in restantes
                  if f.x <= n.x < f.x + f.w and f.y <= n.y < f.y + f.h]  # fmt: skip
        for n in dentro:
            no_elemento(c, n.elemento, n.x, n.y, n.w, n.h)
            restantes.remove(n)
    for n in restantes:
        no_elemento(view, n.elemento, n.x, n.y, n.w, n.h)

    rel_por_id = {r.id: r for r in m.relacoes}
    for conexao in v.conexoes:
        r = rel_por_id.get(conexao.relacao)
        if not r or r.origem not in no_por_elemento or r.destino not in no_por_elemento:
            continue
        con = etree.SubElement(view, _q("connection"), identifier=novo_id(),
                               relationshipRef=r.id, source=no_por_elemento[r.origem],
                               target=no_por_elemento[r.destino])  # fmt: skip
        con.set(f"{{{XSI}}}type", "Relationship")


class _LocalResolver(etree.Resolver):
    """Resolve o xml.xsd e o dc.xsd localmente, sem rede (RNF-06)."""

    def __init__(self, pasta: Path) -> None:
        super().__init__()
        self.pasta = pasta

    def resolve(self, system_url: str, public_id: str, context: Any = None) -> Any:
        nome = system_url.rsplit("/", 1)[-1]
        local = self.pasta / nome
        if local.exists():
            return self.resolve_filename(str(local), context)  # type: ignore[attr-defined]
        return None


@lru_cache(maxsize=4)
def carregar_schema(xsd_dir: Path) -> etree.XMLSchema:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    parser.resolvers.add(_LocalResolver(xsd_dir))
    doc = etree.parse(str(xsd_dir / "archimate3_Diagram.xsd"), parser)
    return etree.XMLSchema(doc)


def parse_seguro(dados: bytes) -> etree._Element:
    """XML sem entidades externas, DTD nem rede (proteção contra XXE)."""
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                             huge_tree=False)  # fmt: skip
    return etree.fromstring(dados, parser)


def validar_v1(xml: bytes, xsd_dir: Path) -> list[Achado]:
    schema = carregar_schema(xsd_dir)
    try:
        doc = parse_seguro(xml)
    except etree.XMLSyntaxError as exc:
        return [Achado(criterio="V1", regra="XML", severidade="erro", mensagem=str(exc))]
    if schema.validate(doc):
        return []
    return [
        Achado(
            criterio="V1", regra="XSD", severidade="erro", mensagem=f"linha {e.line}: {e.message}"
        )
        for e in list(schema.error_log)[:20]  # type: ignore[call-overload]
    ]

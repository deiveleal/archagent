"""Leitura e validação das entradas (spec §4.2, RNF-06, RNF-07, §12).

Nada aqui usa LLM: texto, transcrições, `.docx` e `.drawio` viram linhas
normalizadas com a sua localização; imagens são só validadas e reduzidas.
"""

from __future__ import annotations

import base64
import html
import io
import re
import urllib.parse
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import PurePath

from lxml import etree

MB = 1024 * 1024
LIMITES = {"transcricao": 5 * MB, "texto": 5 * MB, "desenho_drawio": 5 * MB,
           "desenho_imagem": 10 * MB}  # fmt: skip
LADO_MAXIMO_IMAGEM = 2048

FORMATOS = {
    "txt": "transcricao", "md": "transcricao", "vtt": "transcricao", "srt": "transcricao",
    "docx": "transcricao", "drawio": "desenho_drawio", "xml": "desenho_drawio",
    "png": "desenho_imagem", "jpg": "desenho_imagem", "jpeg": "desenho_imagem",
}  # fmt: skip


class EntradaInvalida(ValueError):
    """Arquivo recusado: tipo, conteúdo ou tamanho (RF-ENT-05)."""


@dataclass
class Linha:
    local: str
    texto: str
    falante: str | None = None


@dataclass
class EntradaLida:
    tipo: str
    formato: str
    linhas: list[Linha] = field(default_factory=list)
    imagem_b64: str | None = None
    imagem_mime: str | None = None
    desenho: Desenho | None = None

    def texto_normalizado(self) -> str:
        """Texto com o local de cada linha entre colchetes, para citar a origem."""
        partes = []
        for ln in self.linhas:
            quem = f"{ln.falante}: " if ln.falante else ""
            partes.append(f"[{ln.local}] {quem}{ln.texto}")
        return "\n".join(partes)


# ------------------------------------------------------------------ detecção


def _extensao(nome: str) -> str:
    return PurePath(nome).suffix.lower().lstrip(".")


def detectar(nome: str, dados: bytes) -> tuple[str, str]:
    """Valida extensão, assinatura do conteúdo e tamanho. Devolve (tipo, formato)."""
    ext = _extensao(nome)
    tipo = FORMATOS.get(ext)
    if not tipo:
        aceitos = ", ".join(f".{e}" for e in sorted(FORMATOS))
        raise EntradaInvalida(f"Tipo de arquivo '.{ext}' não aceito. Aceitos: {aceitos}.")
    if not dados:
        raise EntradaInvalida(f"O arquivo '{nome}' está vazio.")
    limite = LIMITES[tipo]
    if len(dados) > limite:
        raise EntradaInvalida(
            f"O arquivo '{nome}' tem {len(dados) / MB:.1f} MB; o limite é {limite // MB} MB."
        )
    formato = "jpg" if ext == "jpeg" else ("drawio" if ext == "xml" else ext)
    if formato == "drawio" and (b"<!DOCTYPE" in dados[:4096] or b"<!ENTITY" in dados[:4096]):
        raise EntradaInvalida("O desenho contém DTD ou entidades; arquivo recusado (XXE).")
    ok = {
        "png": dados.startswith(b"\x89PNG\r\n\x1a\n"),
        "jpg": dados.startswith(b"\xff\xd8\xff"),
        "docx": dados.startswith(b"PK\x03\x04") and _e_docx(dados),
        "drawio": _parece_drawio(dados),
    }.get(formato, _parece_texto(dados))
    if not ok:
        raise EntradaInvalida(f"O conteúdo de '{nome}' não corresponde à extensão .{ext}.")
    return tipo, formato


def _e_docx(dados: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            return "word/document.xml" in z.namelist()
    except zipfile.BadZipFile:
        return False


def _parece_texto(dados: bytes) -> bool:
    if b"\x00" in dados[:8192]:
        return False
    try:
        decodificar(dados)
    except EntradaInvalida:
        return False
    return True


def _parece_drawio(dados: bytes) -> bool:
    inicio = dados[:2048].lstrip().lower()
    if inicio.startswith(b"<?xml"):
        inicio = inicio.split(b"?>", 1)[-1].lstrip()
    return inicio.startswith((b"<mxfile", b"<mxgraphmodel", b"<diagram"))


def decodificar(dados: bytes) -> str:
    """UTF-8 (com ou sem BOM); senão, Windows-1252/Latin-1."""
    for cod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return dados.decode(cod)
        except UnicodeDecodeError:
            continue
    raise EntradaInvalida("Codificação de texto não reconhecida.")


# ------------------------------------------------------------------ texto e transcrições


def ler_texto(texto: str) -> list[Linha]:
    return [Linha(f"linha {i}", ln.strip()) for i, ln in enumerate(texto.splitlines(), 1)
            if ln.strip()]  # fmt: skip


_TEMPO = re.compile(
    r"(\d{1,2}:)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{1,2}:)?(\d{2}):(\d{2})[.,](\d{3})"
)
_VOZ = re.compile(r"<v(?:\.[^\s>]+)?\s+([^>]+)>")
_TAG = re.compile(r"</?[^>]+>")
_FALANTE = re.compile(r"^([A-ZÀ-Ý][\wÀ-ÿ .()\-]{0,40}):\s+(.+)$")


def _tempo(h: str | None, m: str, s: str) -> str:
    return f"{int((h or '0:')[:-1]):02d}:{m}:{s}"


def ler_legenda(texto: str) -> list[Linha]:
    """Lê `.vtt` e `.srt`, preservando tempos e quem fala (RF-ENT-02)."""
    linhas: list[Linha] = []
    blocos = re.split(r"\n\s*\n", texto.replace("\r\n", "\n").strip())
    for bloco in blocos:
        partes = bloco.strip().split("\n")
        idx = next((i for i, p in enumerate(partes) if _TEMPO.search(p)), None)
        if idx is None:
            continue
        g = _TEMPO.search(partes[idx])
        if g is None:
            continue
        local = f"{_tempo(g[1], g[2], g[3])}–{_tempo(g[5], g[6], g[7])}"
        bruto = " ".join(p.strip() for p in partes[idx + 1 :] if p.strip())
        falante = None
        voz = _VOZ.search(bruto)
        if voz:
            falante = voz.group(1).strip()
        conteudo = html.unescape(_TAG.sub("", bruto)).strip()
        if not falante:
            m = _FALANTE.match(conteudo)
            if m:
                falante, conteudo = m.group(1).strip(), m.group(2).strip()
        if conteudo:
            linhas.append(Linha(local, conteudo, falante))
    return linhas


def ler_docx(dados: bytes) -> list[Linha]:
    from docx import Document

    try:
        doc = Document(io.BytesIO(dados))
    except Exception as exc:
        raise EntradaInvalida(f"Não foi possível ler o .docx: {exc}") from exc
    linhas = []
    for i, p in enumerate(doc.paragraphs, 1):
        texto = p.text.strip()
        if not texto:
            continue
        m = _FALANTE.match(texto)
        if m:
            linhas.append(Linha(f"parágrafo {i}", m.group(2).strip(), m.group(1).strip()))
        else:
            linhas.append(Linha(f"parágrafo {i}", texto))
    for t, tabela in enumerate(doc.tables, 1):
        for r, linha in enumerate(tabela.rows, 1):
            celulas = [c.text.strip() for c in linha.cells if c.text.strip()]
            if celulas:
                linhas.append(Linha(f"tabela {t}, linha {r}", " | ".join(celulas)))
    return linhas


# ------------------------------------------------------------------ drawio


@dataclass
class Forma:
    id: str
    texto: str
    estilo: str
    grupo: str | None = None


@dataclass
class Ligacao:
    id: str
    de: str | None
    para: str | None
    rotulo: str


@dataclass
class Pagina:
    nome: str
    formas: list[Forma] = field(default_factory=list)
    ligacoes: list[Ligacao] = field(default_factory=list)


@dataclass
class Desenho:
    paginas: list[Pagina] = field(default_factory=list)


def _xml_seguro(dados: bytes | str) -> etree._Element:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                             huge_tree=False, dtd_validation=False)  # fmt: skip
    if isinstance(dados, str):
        dados = dados.encode("utf-8")
    if b"<!DOCTYPE" in dados[:4096] or b"<!ENTITY" in dados[:4096]:
        raise EntradaInvalida("O desenho contém DTD ou entidades; arquivo recusado (XXE).")
    try:
        return etree.fromstring(dados, parser)
    except etree.XMLSyntaxError as exc:
        raise EntradaInvalida(f"XML do desenho inválido: {exc}") from exc


def _descomprimir(texto: str) -> str:
    """Formato comprimido do draw.io: base64 → deflate cru → URL-encoded."""
    try:
        bruto = zlib.decompress(base64.b64decode(texto.strip()), -15)
    except (ValueError, zlib.error) as exc:
        raise EntradaInvalida(f"Página comprimida do .drawio ilegível: {exc}") from exc
    return urllib.parse.unquote(bruto.decode("utf-8"))


def _limpar_rotulo(valor: str) -> str:
    sem_tags = re.sub(r"<br\s*/?>", " ", valor, flags=re.IGNORECASE)
    sem_tags = re.sub(r"<[^>]+>", " ", sem_tags)
    return re.sub(r"\s+", " ", html.unescape(sem_tags)).strip()


def ler_drawio(dados: bytes) -> Desenho:
    """Lê páginas, formas, textos, ligações e agrupamentos sem LLM (RF-ENT-03)."""
    raiz = _xml_seguro(dados)
    if raiz.tag == "mxGraphModel":
        modelos = [("Página 1", raiz)]
    else:
        diagramas = raiz.findall("diagram") if raiz.tag == "mxfile" else [raiz]
        modelos = []
        for i, d in enumerate(diagramas, 1):
            nome = d.get("name") or f"Página {i}"
            m = d.find("mxGraphModel")
            if m is None and (d.text or "").strip():
                m = _xml_seguro(_descomprimir(d.text or ""))
            if m is not None:
                modelos.append((nome, m))
    desenho = Desenho()
    for nome, modelo in modelos:
        celulas = {c.get("id", ""): c for c in modelo.iter("mxCell")}
        objetos = {o.get("id", ""): o for o in modelo.iter("object", "UserObject")}
        pagina = Pagina(nome)

        def rotulo(
            cid: str,
            objetos: dict[str, etree._Element] = objetos,
            celulas: dict[str, etree._Element] = celulas,
        ) -> str:
            obj = objetos.get(cid)
            if obj is not None:
                return _limpar_rotulo(obj.get("label", ""))
            c = celulas.get(cid)
            return _limpar_rotulo(c.get("value", "") if c is not None else "")

        # Células dentro de <object> herdam o id do objeto.
        for oid, obj in objetos.items():
            interna = obj.find("mxCell")
            if interna is not None:
                interna.set("id", oid)
                celulas[oid] = interna
        grupos = {cid for cid, c in celulas.items()
                  if c.get("vertex") == "1"
                  and any(x.get("parent") == cid for x in celulas.values())}  # fmt: skip
        for cid, c in celulas.items():
            if not cid:
                continue
            if c.get("vertex") == "1":
                texto = rotulo(cid)
                pai = c.get("parent")
                grupo = rotulo(pai) if pai in grupos else None
                if cid in grupos:
                    continue
                if texto or "text" not in (c.get("style") or ""):
                    pagina.formas.append(Forma(cid, texto, c.get("style", ""), grupo or None))
            elif c.get("edge") == "1":
                pagina.ligacoes.append(Ligacao(cid, c.get("source"), c.get("target"),
                                               rotulo(cid)))  # fmt: skip
        # Grupos também aparecem, como formas que agrupam.
        for g in sorted(grupos):
            if g in celulas and rotulo(g):
                pagina.formas.append(Forma(g, rotulo(g), "grupo"))
        desenho.paginas.append(pagina)
    return desenho


def desenho_em_linhas(desenho: Desenho) -> list[Linha]:
    linhas: list[Linha] = []
    for p in desenho.paginas:
        nomes = {f.id: f.texto or f"(forma sem texto {f.id})" for f in p.formas}
        for f in p.formas:
            if f.estilo == "grupo":
                membros = [x.texto for x in p.formas if x.grupo == f.texto and x.texto]
                linhas.append(Linha(f"página '{p.nome}' / grupo '{f.texto}'",
                                    f"Grupo '{f.texto}' contém: {', '.join(membros)}"))  # fmt: skip
                continue
            texto = f.texto or "(sem texto)"
            extra = f" (dentro do grupo '{f.grupo}')" if f.grupo else ""
            forma = _forma_legivel(f.estilo)
            linhas.append(Linha(f"página '{p.nome}' / forma '{texto}'",
                                f"Forma{forma}: {texto}{extra}"))  # fmt: skip
        for lg in p.ligacoes:
            de = nomes.get(lg.de or "", "(sem origem)")
            para = nomes.get(lg.para or "", "(sem destino)")
            rot = f" — rótulo: '{lg.rotulo}'" if lg.rotulo else ""
            linhas.append(Linha(f"página '{p.nome}' / ligação '{de}' → '{para}'",
                                f"Ligação de '{de}' para '{para}'{rot}"))  # fmt: skip
    return linhas


def _forma_legivel(estilo: str) -> str:
    for chave, nome in (("umlActor", "ator"), ("cylinder", "cilindro/banco"), ("cube", "cubo"),
                        ("note", "nota/documento"), ("cloud", "nuvem"), ("phone", "celular"),
                        ("dashed=1", "tracejada"), ("rounded=1", "arredondada")):  # fmt: skip
        if chave in estilo:
            return f" ({nome})"
    return ""


# ------------------------------------------------------------------ imagens


def preparar_imagem(dados: bytes) -> tuple[str, str]:
    """Valida a imagem e reduz o lado maior a 2048 px (spec §12). Devolve (b64, mime)."""
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(dados)) as conferir:
            conferir.verify()
        aberta = Image.open(io.BytesIO(dados))
        aberta.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise EntradaInvalida(f"Imagem ilegível: {exc}") from exc
    formato = "PNG" if aberta.format == "PNG" else "JPEG"
    img: Image.Image = aberta
    if max(img.size) > LADO_MAXIMO_IMAGEM:
        img.thumbnail((LADO_MAXIMO_IMAGEM, LADO_MAXIMO_IMAGEM))
    if formato == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    saida = io.BytesIO()
    img.save(saida, format=formato)
    mime = "image/png" if formato == "PNG" else "image/jpeg"
    return base64.b64encode(saida.getvalue()).decode("ascii"), mime


# ------------------------------------------------------------------ fachada


def ler_entrada(nome: str, dados: bytes) -> EntradaLida:
    tipo, formato = detectar(nome, dados)
    if formato in ("vtt", "srt"):
        linhas = ler_legenda(decodificar(dados))
        return EntradaLida(tipo, formato, linhas)
    if formato in ("txt", "md"):
        return EntradaLida(tipo, formato, ler_texto(decodificar(dados)))
    if formato == "docx":
        return EntradaLida(tipo, formato, ler_docx(dados))
    if formato == "drawio":
        desenho = ler_drawio(dados)
        return EntradaLida(tipo, formato, desenho_em_linhas(desenho), desenho=desenho)
    b64, mime = preparar_imagem(dados)
    return EntradaLida(tipo, formato, imagem_b64=b64, imagem_mime=mime)


def ler_mensagem(texto: str) -> EntradaLida:
    if not texto.strip():
        raise EntradaInvalida("Mensagem vazia.")
    if len(texto.encode()) > LIMITES["texto"]:
        raise EntradaInvalida("Mensagem acima de 5 MB.")
    return EntradaLida("texto", "texto", ler_texto(texto))

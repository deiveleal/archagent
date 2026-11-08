from __future__ import annotations

import base64
import io
import urllib.parse
import zlib
from pathlib import Path

import pytest
from docx import Document
from PIL import Image

from archagent.core.inputs import (
    EntradaInvalida,
    decodificar,
    desenho_em_linhas,
    detectar,
    ler_drawio,
    ler_entrada,
    ler_legenda,
    ler_mensagem,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

VTT = """WEBVTT

00:00:01.000 --> 00:00:05.500
<v Ana (RH)>O Sistema de RH manda o arquivo.

00:01:02.000 --> 00:01:09.000
<v.loud Bruno>A Folha &amp; o Ponto.
"""

SRT = """1
00:00:02,000 --> 00:00:08,000
Carla: O cliente paga o pedido.

2
01:00:08,500 --> 01:00:15,000
sem falante aqui
"""


def test_vtt_tempos_e_falantes() -> None:
    linhas = ler_legenda(VTT)
    assert [(ln.local, ln.falante) for ln in linhas] == [
        ("00:00:01–00:00:05", "Ana (RH)"),
        ("00:01:02–00:01:09", "Bruno"),
    ]
    assert linhas[1].texto == "A Folha & o Ponto."


def test_srt_tempos_e_falantes() -> None:
    linhas = ler_legenda(SRT)
    assert linhas[0].falante == "Carla"
    assert linhas[0].texto == "O cliente paga o pedido."
    assert linhas[1].local == "01:00:08–01:00:15"
    assert linhas[1].falante is None


def test_txt_e_md_com_linhas() -> None:
    e = ler_entrada("nota.md", "# Título\n\nO portal chama a API.\n".encode())
    assert e.tipo == "transcricao"
    assert e.texto_normalizado() == "[linha 1] # Título\n[linha 3] O portal chama a API."


def test_codificacao_latin1() -> None:
    assert decodificar("Ação".encode("cp1252")) == "Ação"
    e = ler_entrada("a.txt", "Reunião sobre integração".encode("latin-1"))
    assert "Reunião" in e.linhas[0].texto


def test_docx() -> None:
    doc = Document()
    doc.add_paragraph("Ana: O RH usa o Sistema de RH.")
    doc.add_paragraph("")
    doc.add_paragraph("Decisão tomada.")
    t = doc.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text = "Sistema"
    t.rows[0].cells[1].text = "Folha"
    buf = io.BytesIO()
    doc.save(buf)
    e = ler_entrada("ata.docx", buf.getvalue())
    assert e.linhas[0].falante == "Ana"
    assert e.linhas[1].local == "parágrafo 3"
    assert e.linhas[2].texto == "Sistema | Folha"


@pytest.mark.parametrize("nome", ["vazio.txt", "vazio.vtt"])
def test_arquivo_vazio(nome: str) -> None:
    with pytest.raises(EntradaInvalida, match="vazio"):
        ler_entrada(nome, b"")


def test_upload_tipo_nao_aceito() -> None:
    with pytest.raises(EntradaInvalida, match="não aceito"):
        detectar("planilha.xlsx", b"PK")


def test_upload_extensao_com_conteudo_errado() -> None:
    with pytest.raises(EntradaInvalida, match="não corresponde"):
        detectar("foto.png", b"\xff\xd8\xff isto e jpg")
    with pytest.raises(EntradaInvalida, match="não corresponde"):
        detectar("ata.docx", b"texto puro")
    with pytest.raises(EntradaInvalida, match="não corresponde"):
        detectar("notas.txt", b"\x00\x01\x02binario")


def test_upload_acima_do_limite() -> None:
    with pytest.raises(EntradaInvalida, match="limite"):
        detectar("grande.txt", b"a" * (5 * 1024 * 1024 + 1))


def test_mensagem() -> None:
    assert ler_mensagem("olá\nmundo").linhas[1].local == "linha 2"
    with pytest.raises(EntradaInvalida):
        ler_mensagem("   ")


# ------------------------------------------------------------------ drawio


def test_drawio_exemplo_formas_ligacoes_grupos() -> None:
    dados = (FIXTURES / "drawio" / "entregas.drawio").read_bytes()
    d = ler_drawio(dados)
    p = d.paginas[0]
    textos = {f.texto for f in p.formas}
    assert {"Entregador", "API de Rotas", "Serviço de Mapas (externo)", "Nuvem"} <= textos
    api = next(f for f in p.formas if f.texto == "API de Rotas")
    assert api.grupo == "Nuvem"
    rotulos = {lg.rotulo for lg in p.ligacoes}
    assert "REST" in rotulos
    linhas = desenho_em_linhas(d)
    assert any("Ligação de 'App do Entregador' para 'API de Rotas'" in ln.texto for ln in linhas)
    assert any(ln.texto.startswith("Grupo 'Nuvem' contém") for ln in linhas)


def _comprimir(xml: str) -> str:
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    bruto = c.compress(urllib.parse.quote(xml).encode()) + c.flush()
    return base64.b64encode(bruto).decode()


MODELO = (
    '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="a" value="Portal" vertex="1" parent="1"/>'
    '<mxCell id="b" value="" vertex="1" parent="1" style="ellipse"/>'
    '<mxCell id="e" value="chama" edge="1" parent="1" source="a"/>'
    "</root></mxGraphModel>"
)


def test_drawio_comprimido_varias_paginas_forma_sem_texto_ligacao_sem_destino() -> None:
    xml = (
        f'<mxfile><diagram name="P1">{_comprimir(MODELO)}</diagram>'
        f'<diagram name="P2">{MODELO}</diagram></mxfile>'
    ).encode()
    d = ler_drawio(xml)
    assert [p.nome for p in d.paginas] == ["P1", "P2"]
    p1 = d.paginas[0]
    assert any(f.texto == "" for f in p1.formas)
    assert p1.ligacoes[0].para is None
    linhas = desenho_em_linhas(d)
    assert any("(sem destino)" in ln.texto for ln in linhas)
    assert any("(sem texto)" in ln.texto for ln in linhas)


def test_drawio_com_object() -> None:
    xml = (
        b'<mxfile><diagram name="P"><mxGraphModel><root><mxCell id="0"/>'
        b'<mxCell id="1" parent="0"/><object id="x" label="Banco &lt;b&gt;MySQL&lt;/b&gt;">'
        b'<mxCell vertex="1" parent="1" style="shape=cylinder"/></object>'
        b"</root></mxGraphModel></diagram></mxfile>"
    )
    linhas = desenho_em_linhas(ler_drawio(xml))
    assert linhas[0].texto == "Forma (cilindro/banco): Banco MySQL"


def test_drawio_xxe_recusado(tmp_path: Path) -> None:
    segredo = tmp_path / "s.txt"
    segredo.write_text("SEGREDO")
    xml = (
        f'<?xml version="1.0"?><!DOCTYPE m [<!ENTITY x SYSTEM "file://{segredo}">]>'
        '<mxfile><diagram name="&x;"></diagram></mxfile>'
    ).encode()
    with pytest.raises(EntradaInvalida, match="XXE"):
        ler_entrada("mal.drawio", xml)


# ------------------------------------------------------------------ imagens


def _png(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (255, 255, 255)).save(buf, "PNG")
    return buf.getvalue()


def test_imagem_reduzida_a_2048() -> None:
    e = ler_entrada("quadro.png", _png(4000, 1000))
    assert e.imagem_mime == "image/png"
    img = Image.open(io.BytesIO(base64.b64decode(e.imagem_b64 or "")))
    assert img.size == (2048, 512)


def test_imagem_corrompida() -> None:
    with pytest.raises(EntradaInvalida):
        ler_entrada("quadro.png", b"\x89PNG\r\n\x1a\n" + b"lixo" * 10)


def test_imagem_jpeg() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "JPEG")
    assert ler_entrada("f.jpeg", buf.getvalue()).imagem_mime == "image/jpeg"

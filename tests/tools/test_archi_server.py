from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

_spec = importlib.util.spec_from_file_location(
    "archi_server", Path(__file__).resolve().parents[2] / "tools" / "archi" / "server.py"
)
assert _spec and _spec.loader
server = importlib.util.module_from_spec(_spec)
sys.modules["archi_server"] = server
_spec.loader.exec_module(server)


def test_limpar_log_tira_pilha_e_ruido() -> None:
    log = (
        "(Archi:1): Gtk-WARNING **: cannot open display\n"
        "org.xml.sax.SAXParseException; Key 'TargetRef' not found\n"
        "\tat java.xml/com.sun.Foo.bar(Unknown Source)\n"
        "java.io.IOException: Model not set\n"
        "java.io.IOException: Model not set\n"
    )
    limpo = server.limpar_log(log)
    assert limpo.splitlines() == [
        "org.xml.sax.SAXParseException; Key 'TargetRef' not found",
        "java.io.IOException: Model not set",
    ]


def test_comando_usa_xvfb_e_linha_de_comando_do_archi() -> None:
    cmd = server.comando(Path("/t/in.xml"), Path("/t/out.archimate"))
    assert cmd[:2] == ["xvfb-run", "-a"]
    assert "com.archimatetool.commandline.app" in cmd
    assert cmd[-4:] == ["--xmlexchange.import", "/t/in.xml", "--saveModel", "/t/out.archimate"]


def test_convert_sem_corpo() -> None:
    r = TestClient(server.app).post("/convert", content=b"")
    assert r.status_code == 400
    assert r.json()["erro"]["codigo"] == "entrada_vazia"


def test_health_sem_archi_instalado(monkeypatch: object) -> None:
    server.ARCHI_HOME = Path("/nao/existe")
    assert TestClient(server.app).get("/health").json()["status"] == "sem_archi"

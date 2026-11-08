"""API mínima do tool-archi (spec §14).

Converte o Open Exchange Format em `.archimate` com a linha de comando do Archi 5.
Se o Archi falhar ao importar ou salvar, devolve o erro de forma legível (V5).
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

ARCHI_HOME = Path(os.environ.get("ARCHI_HOME", "/opt/Archi"))
ARCHI_VERSION = os.environ.get("ARCHI_VERSION", "desconhecida")
TIMEOUT = float(os.environ.get("ARCHI_TIMEOUT_SECONDS", "150"))
MAX_BYTES = 10 * 1024 * 1024

app = FastAPI(title="tool-archi", version="0.1.0")
# O Archi usa a mesma pasta de configuração (~/.archi); uma conversão por vez.
_lock = threading.Lock()

_RUIDO = re.compile(
    r"(Gtk-WARNING|GLib|dbus|libEGL|MESA|Fontconfig|SWT|at-spi|Xlib|Gdk)", re.IGNORECASE
)


def comando(entrada: Path, saida: Path) -> list[str]:
    return [
        "xvfb-run", "-a", "-s", "-screen 0 1280x1024x24",
        str(ARCHI_HOME / "Archi"),
        "-application", "com.archimatetool.commandline.app",
        "-consoleLog", "-nosplash",
        "--xmlexchange.import", str(entrada),
        "--saveModel", str(saida),
    ]  # fmt: skip


def limpar_log(texto: str) -> str:
    """Tira ruído do GTK e as linhas de pilha Java; mantém as mensagens de erro."""
    linhas: list[str] = []
    for ln in texto.splitlines():
        ln = ln.rstrip()
        if not ln.strip() or _RUIDO.search(ln) or ln.lstrip().startswith(("at ", "...")):
            continue
        if ln not in linhas:
            linhas.append(ln)
    return "\n".join(linhas[-20:])


def erro(status: int, codigo: str, mensagem: str, log: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"erro": {"codigo": codigo, "mensagem": mensagem, "log": log}},
    )


@app.get("/health")
def health() -> dict[str, Any]:
    executavel = ARCHI_HOME / "Archi"
    return {
        "status": "ok" if executavel.exists() else "sem_archi",
        "archi_versao": ARCHI_VERSION,
    }


@app.post("/convert", response_model=None)
async def convert(request: Request) -> Response:
    corpo = await request.body()
    if not corpo:
        return erro(400, "entrada_vazia", "Envie o Exchange Format no corpo da requisição.")
    if len(corpo) > MAX_BYTES:
        return erro(413, "entrada_grande", "Exchange Format acima de 10 MB.")
    with tempfile.TemporaryDirectory() as pasta:
        entrada = Path(pasta) / "modelo.xml"
        saida = Path(pasta) / "modelo.archimate"
        entrada.write_bytes(corpo)
        with _lock:
            try:
                proc = subprocess.run(  # noqa: S603 - argumentos fixos, sem shell
                    comando(entrada, saida), capture_output=True, text=True,
                    timeout=TIMEOUT, check=False,
                )  # fmt: skip
            except subprocess.TimeoutExpired:
                return erro(504, "archi_timeout", f"O Archi não terminou em {TIMEOUT:.0f} s.")
        log = limpar_log(proc.stdout + "\n" + proc.stderr)
        if proc.returncode != 0 or not saida.exists() or saida.stat().st_size == 0:
            return erro(422, "archi_falhou", "O Archi não conseguiu importar ou salvar.", log)
        return Response(
            content=saida.read_bytes(),
            media_type="application/xml",
            headers={"x-archi-version": ARCHI_VERSION},
        )

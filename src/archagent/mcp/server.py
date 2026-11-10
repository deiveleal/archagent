"""Servidor MCP do ArchAgent.

Expõe a API do agente ArchiMate (spec §13) como ferramentas MCP, para que um
cliente como o Claude Code conduza uma sessão inteira: entradas, briefing,
perguntas, modelo e arquivos. Não tem lógica de agente: cada ferramenta é uma
chamada ao `AgenteCliente`, o mesmo usado pela interface.

Uso:
    archagent-mcp                      # stdio (cliente MCP local)
    MCP_TRANSPORT=streamable-http archagent-mcp   # HTTP em /mcp (container)
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from archagent.core.cliente import AgenteCliente, ErroApi

TipoArquivo = Literal["archimate", "exchange", "relatorio"]

INSTRUCOES = """\
ArchAgent: gera modelos ArchiMate 3.2 a partir de transcrições, mensagens e desenhos.

Fluxo típico:
1. criar_sessao (ou listar_sessoes para retomar uma).
2. enviar_texto / enviar_arquivo com o material (transcrição, ata, .drawio, imagem).
3. ver_briefing e listar_perguntas; responder_pergunta com o arquiteto (não invente respostas).
4. confirmar_briefing quando o arquiteto concordar com o briefing.
5. gerar_modelo; depois baixar_arquivo (archimate, exchange ou relatorio).
6. enviar_mensagem para dúvidas, correções e alternativas sobre o modelo.

As entradas vão para a API do DashScope (Alibaba Cloud): não envie dados sensíveis.
"""


class McpSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    agent_archimate_url: str = "http://localhost:8000"
    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    # Hosts aceitos no cabeçalho Host (proteção contra DNS rebinding).
    mcp_allowed_hosts: list[str] = Field(
        default_factory=lambda: ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    )
    mcp_max_bytes_entrada: int = 20 * 1024 * 1024
    # Pasta de onde `enviar_arquivo(caminho=...)` pode ler; vazia = desligado.
    mcp_pasta_arquivos: str = ""
    # Pasta onde `baixar_arquivo` grava os arquivos; vazia = devolve o conteúdo.
    mcp_pasta_saida: str = ""
    mcp_timeout_modelo_segundos: float = 600.0
    mcp_intervalo_consulta_segundos: float = 2.0


def _dentro(base: str, caminho: str) -> Path:
    raiz = Path(base).resolve()
    alvo = (raiz / caminho).resolve()
    if not alvo.is_relative_to(raiz):
        raise ToolError(f"O caminho precisa estar dentro de {raiz}.")
    return alvo


def _item(i: dict[str, Any]) -> dict[str, Any]:
    """Versão enxuta de um item do briefing (economiza contexto do cliente)."""
    return {
        "id": i["id"],
        "tipo": i["tipo"],
        "nome": i["nome"],
        "descricao": i.get("descricao", ""),
        "confianca": i.get("confianca"),
        "status": i["status"],
        "origens": [f"{o['entrada']} {o.get('local', '')}".strip() for o in i.get("origens", [])],
        **({"superado_por": i["superado_por"]} if i.get("superado_por") else {}),
    }


def _pergunta(p: dict[str, Any]) -> dict[str, Any]:
    return {k: p.get(k) for k in ("id", "item", "texto", "impacto", "status")}


def _resumo_modelo(m: dict[str, Any]) -> dict[str, Any]:
    v = m["validacao"]
    nomes = {e["id"]: e["nome"] for e in m["elementos"]}
    return {
        "id": m["id"],
        "viavel": v["viavel"],
        "criterios": v["criterios"],
        "erros": [f"{a['criterio']} {a['regra']}: {a['mensagem']}" for a in v["erros"]],
        "avisos": [f"{a['criterio']} {a['regra']}: {a['mensagem']}" for a in v["avisos"]],
        "rodadas_correcao": m.get("rodadas_correcao", 0),
        "elementos": [
            {"tipo": e["tipo"], "nome": e["nome"], **({"premissa": True} if e["premissa"] else {})}
            for e in m["elementos"]
        ],
        "relacoes": [
            f"{nomes.get(r['origem'], r['origem'])} —{r['tipo']}→ "
            f"{nomes.get(r['destino'], r['destino'])}"
            for r in m["relacoes"]
        ],
        "visoes": [x["nome"] for x in m["visoes"]],
    }


def criar_servidor(
    settings: McpSettings | None = None, cliente: AgenteCliente | None = None
) -> MCPServer:
    cfg = settings or McpSettings()
    api = cliente or AgenteCliente(cfg.agent_archimate_url)
    mcp: MCPServer = MCPServer("archagent", instructions=INSTRUCOES, version="0.1.0")

    def chamar(fn: Any, *args: Any, **kw: Any) -> Any:
        try:
            return fn(*args, **kw)
        except ErroApi as exc:
            raise ToolError(f"{exc.mensagem} ({exc.codigo})") from exc

    def resumo_entrada(r: dict[str, Any]) -> dict[str, Any]:
        e = r.get("entrada", {})
        return {
            "entrada": {k: e.get(k) for k in ("id", "tipo", "formato", "status", "observacao")},
            "resultado": r.get("resultado", {}),
            "perguntas": [_pergunta(p) for p in r.get("perguntas", [])],
        }

    @mcp.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
    async def saude(_: Request) -> Response:
        return JSONResponse({"status": "ok"})

    # ------------------------------------------------------------ sessões

    @mcp.tool()
    def listar_sessoes() -> dict[str, Any]:
        """Lista as sessões de modelagem existentes (id, título, status)."""
        sessoes = chamar(api.sessoes)
        return {"sessoes": [{k: s.get(k) for k in ("id", "titulo", "status")} for s in sessoes]}

    @mcp.tool()
    def criar_sessao(titulo: str) -> dict[str, Any]:
        """Cria uma sessão de modelagem. Uma sessão = um sistema ou iniciativa a modelar."""
        return {"sessao": chamar(api.criar_sessao, titulo)}

    @mcp.tool()
    def ver_sessao(sessao: str) -> dict[str, Any]:
        """Status da sessão, entradas recebidas, últimas mensagens e uso de tokens."""
        d = chamar(api.sessao, sessao)
        return {
            "sessao": d["sessao"],
            "entradas": [
                {k: e.get(k) for k in ("id", "nome_arquivo", "tipo", "formato", "status")}
                for e in d.get("entradas", [])
            ],
            "conversa": d.get("conversa", [])[-10:],
            "uso": {k: v for k, v in chamar(api.uso, sessao).items() if k != "request_id"},
        }

    # ------------------------------------------------------------ entradas e conversa

    @mcp.tool()
    def enviar_texto(sessao: str, texto: str) -> dict[str, Any]:
        """Envia material para interpretar (transcrição, ata, descrição do sistema).

        O agente extrai itens para o briefing, com a origem de cada um, e pode
        devolver perguntas de esclarecimento.
        """
        return resumo_entrada(chamar(api.enviar_texto, sessao, texto))

    @mcp.tool()
    def enviar_arquivo(
        sessao: str,
        nome: str,
        conteudo: str | None = None,
        conteudo_base64: str | None = None,
        caminho: str | None = None,
    ) -> dict[str, Any]:
        """Envia um arquivo de entrada: .txt, .md, .vtt, .srt, .docx, .drawio, .png ou .jpg.

        Passe exatamente uma fonte: `conteudo` (arquivos de texto), `conteudo_base64`
        (binários como .docx e imagens) ou `caminho` (relativo à pasta configurada
        em MCP_PASTA_ARQUIVOS). `nome` define o formato pela extensão.
        """
        fontes = [x for x in (conteudo, conteudo_base64, caminho) if x is not None]
        if len(fontes) != 1:
            raise ToolError("Passe exatamente um de: conteudo, conteudo_base64, caminho.")
        if conteudo is not None:
            dados = conteudo.encode("utf-8")
        elif conteudo_base64 is not None:
            try:
                dados = base64.b64decode(conteudo_base64, validate=True)
            except ValueError as exc:
                raise ToolError("conteudo_base64 inválido.") from exc
        else:
            if not cfg.mcp_pasta_arquivos:
                raise ToolError("Leitura por caminho desligada (defina MCP_PASTA_ARQUIVOS).")
            arq = _dentro(cfg.mcp_pasta_arquivos, str(caminho))
            if not arq.is_file():
                raise ToolError(f"Arquivo não encontrado: {caminho}")
            dados = arq.read_bytes()
        if len(dados) > cfg.mcp_max_bytes_entrada:
            raise ToolError(f"Arquivo maior que {cfg.mcp_max_bytes_entrada} bytes.")
        return resumo_entrada(chamar(api.enviar_arquivo, sessao, nome, dados))

    @mcp.tool()
    def enviar_mensagem(sessao: str, texto: str) -> dict[str, Any]:
        """Conversa com o agente sobre a sessão: dúvidas, correções, alternativas e comandos.

        Correções atualizam o briefing; pedidos de alternativa devolvem prós e contras.
        """
        r = chamar(api.enviar_mensagem, sessao, texto)
        return {k: v for k, v in r.items() if k != "request_id"}

    # ------------------------------------------------------------ briefing e perguntas

    @mcp.tool()
    def ver_briefing(sessao: str, incluir_inativos: bool = False) -> dict[str, Any]:
        """Itens do briefing (atores, processos, sistemas, dados, conflitos, pendências...)."""
        b = chamar(api.briefing, sessao)
        itens = [i for i in b["itens"] if incluir_inativos or i["status"] == "ativo"]
        return {"confirmado_em": b["confirmado_em"], "itens": [_item(i) for i in itens]}

    @mcp.tool()
    def listar_perguntas(sessao: str) -> dict[str, Any]:
        """Perguntas de esclarecimento pendentes. Leve-as ao arquiteto; não invente respostas."""
        return {"perguntas": [_pergunta(p) for p in chamar(api.perguntas, sessao)]}

    @mcp.tool()
    def responder_pergunta(
        sessao: str, pergunta: str, resposta: str | None = None, pular: bool = False
    ) -> dict[str, Any]:
        """Responde (ou pula) uma pergunta de esclarecimento; o briefing é atualizado."""
        if not pular and not (resposta and resposta.strip()):
            raise ToolError("Passe a resposta ou pular=true.")
        r = chamar(api.responder, sessao, pergunta, resposta, pular)
        return {
            "pergunta": _pergunta(r["pergunta"]),
            "perguntas_pendentes": [_pergunta(p) for p in r.get("perguntas_pendentes", [])],
        }

    @mcp.tool()
    def confirmar_briefing(sessao: str) -> dict[str, Any]:
        """Confirma o briefing. Só depois disso o modelo pode ser gerado."""
        r = chamar(api.confirmar, sessao)
        return {k: v for k, v in r.items() if k != "request_id"}

    # ------------------------------------------------------------ modelos

    @mcp.tool()
    def gerar_modelo(sessao: str, aguardar: bool = True) -> dict[str, Any]:
        """Gera uma nova versão do modelo ArchiMate a partir do briefing confirmado.

        Valida (V1–V5), corrige até 3 vezes e converte para .archimate. Leva de
        30 s a alguns minutos. Com aguardar=false, devolve o job e o modelo
        pode ser consultado depois com ver_modelo.
        """
        job = chamar(api.gerar_modelo, sessao)
        if not aguardar:
            return {"job": job["job_id"], "modelo": job["modelo"], "status": job["status"]}
        limite = time.monotonic() + cfg.mcp_timeout_modelo_segundos
        info = job
        while info["status"] == "em_andamento":
            if time.monotonic() > limite:
                return {
                    "job": job["job_id"],
                    "modelo": job["modelo"],
                    "status": "em_andamento",
                    "aviso": "Ainda gerando; consulte ver_modelo mais tarde.",
                }
            time.sleep(cfg.mcp_intervalo_consulta_segundos)
            info = chamar(api.job, sessao, job["job_id"])
        if info["status"] == "falhou":
            raise ToolError(f"A geração falhou: {info.get('erro', 'erro desconhecido')}")
        return _resumo_modelo(chamar(api.modelo, sessao, job["modelo"]))

    @mcp.tool()
    def ver_modelo(sessao: str, modelo: str | None = None) -> dict[str, Any]:
        """Validação, elementos, relações e visões de uma versão (padrão: a mais recente)."""
        versoes = chamar(api.modelos, sessao)
        if not versoes:
            raise ToolError("A sessão ainda não tem modelo.")
        mid = modelo or versoes[-1]["id"]
        return {
            "versoes": [{"id": v["id"], "viavel": v["viavel"]} for v in versoes],
            "modelo": _resumo_modelo(chamar(api.modelo, sessao, mid)),
        }

    @mcp.tool()
    def baixar_arquivo(sessao: str, modelo: str, tipo: TipoArquivo) -> dict[str, Any]:
        """Baixa um arquivo do modelo: `archimate` (abre no Archi), `exchange` (XML
        Open Group) ou `relatorio` (Markdown de viabilidade).

        Com MCP_PASTA_SAIDA configurada, grava lá e devolve o caminho; senão,
        devolve o conteúdo para o cliente salvar.
        """
        dados: bytes = chamar(api.arquivo, sessao, modelo, tipo)
        ext = {"archimate": "archimate", "exchange": "xml", "relatorio": "md"}[tipo]
        nome = f"{sessao}-{modelo}.{ext}"
        if cfg.mcp_pasta_saida:
            destino = _dentro(cfg.mcp_pasta_saida, nome)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados)
            return {"arquivo": nome, "caminho": str(destino), "bytes": len(dados)}
        return {"arquivo": nome, "bytes": len(dados), "conteudo": dados.decode("utf-8")}

    return mcp


def main() -> None:
    cfg = McpSettings()
    servidor = criar_servidor(cfg)
    if cfg.mcp_transport == "stdio":
        servidor.run("stdio")
        return
    servidor.run(
        "streamable-http",
        host=cfg.mcp_host,
        port=cfg.mcp_port,
        max_request_body_size=cfg.mcp_max_bytes_entrada * 2,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=cfg.mcp_allowed_hosts,
            allowed_origins=[f"http://{h}" for h in cfg.mcp_allowed_hosts],
        ),
    )


if __name__ == "__main__":
    main()

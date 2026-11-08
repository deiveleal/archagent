"""Cliente LLM do núcleo (DashScope pela API compatível com OpenAI).

- Saída estruturada: JSON validado por um modelo Pydantic (spec RF-MOD-02).
- Tempo limite e novas tentativas com espera crescente (RNF-04).
- Registro de consumo por chamada, sem conteúdo (RNF-10).
- Modo "replay" para os testes: respostas gravadas em arquivos; sem gravação, falha.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from archagent.core.config import Settings
from archagent.core.logs import log_event

logger = logging.getLogger(__name__)

Message = dict[str, Any]


class LLMError(RuntimeError):
    """Falha ao chamar o LLM ou ao interpretar a resposta."""


class TokenBudgetExceeded(LLMError):
    """Limite de tokens da sessão atingido (RNF-03)."""


class MissingFixture(LLMError):
    """Modo replay sem gravação para a chamada."""


@dataclass
class LLMResult:
    texto: str
    tokens_entrada: int = 0
    tokens_saida: int = 0
    latencia_ms: int = 0
    modelo: str = ""

    @property
    def tokens(self) -> int:
        return self.tokens_entrada + self.tokens_saida


class ChatBackend(Protocol):
    def chat(
        self, messages: Sequence[Message], *, modelo: str, json_mode: bool, no: str
    ) -> LLMResult: ...


def image_message(texto: str, imagem_b64: str, mime: str = "image/png") -> Message:
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": texto},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{imagem_b64}"}},
        ],
    }


class DashScopeBackend:
    def __init__(self, settings: Settings) -> None:
        from openai import OpenAI

        self._settings = settings
        self._client = OpenAI(
            api_key=settings.dashscope_api_key.get_secret_value() or "sem-chave",
            base_url=settings.dashscope_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )

    def chat(
        self, messages: Sequence[Message], *, modelo: str, json_mode: bool, no: str
    ) -> LLMResult:
        import openai

        kwargs: dict[str, Any] = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if self._settings.llm_temperature is not None:
            kwargs["temperature"] = self._settings.llm_temperature
        kwargs["extra_body"] = {"enable_thinking": self._settings.llm_enable_thinking}
        tentativas = max(1, self._settings.llm_max_retries)
        ultimo_erro: Exception | None = None
        for tentativa in range(1, tentativas + 1):
            inicio = time.monotonic()
            try:
                resp = self._client.chat.completions.create(
                    model=modelo,
                    messages=list(messages),  # type: ignore[arg-type]
                    **kwargs,
                )
            except (
                openai.APITimeoutError,
                openai.APIConnectionError,
                openai.RateLimitError,
                openai.InternalServerError,
            ) as exc:
                ultimo_erro = exc
                resultado = "timeout" if isinstance(exc, openai.APITimeoutError) else "erro"
                log_event(
                    logger,
                    "llm.chamada",
                    logging.WARNING,
                    no=no,
                    modelo=modelo,
                    resultado=resultado,
                    tentativa=tentativa,
                    tipo_erro=type(exc).__name__,
                )
                if tentativa < tentativas:
                    time.sleep(min(2**tentativa, 20))
                continue
            except openai.APIError as exc:
                log_event(
                    logger,
                    "llm.chamada",
                    logging.ERROR,
                    no=no,
                    modelo=modelo,
                    resultado="erro",
                    tipo_erro=type(exc).__name__,
                )
                raise LLMError(f"Erro do provedor LLM: {type(exc).__name__}") from exc
            latencia = int((time.monotonic() - inicio) * 1000)
            uso = resp.usage
            texto = (resp.choices[0].message.content or "") if resp.choices else ""
            return LLMResult(
                texto=texto,
                tokens_entrada=uso.prompt_tokens if uso else 0,
                tokens_saida=uso.completion_tokens if uso else 0,
                latencia_ms=latencia,
                modelo=modelo,
            )
        raise LLMError(
            f"O provedor LLM não respondeu após {tentativas} tentativas "
            f"({type(ultimo_erro).__name__})."
        )


def fixture_key(no: str, modelo: str, messages: Sequence[Message], json_mode: bool) -> str:
    bruto = json.dumps(
        {"no": no, "modelo": modelo, "json": json_mode, "messages": list(messages)},
        ensure_ascii=False,
        sort_keys=True,
    )
    return f"{no}-{hashlib.sha256(bruto.encode()).hexdigest()[:16]}"


class ReplayBackend:
    """Lê respostas gravadas; com `gravar=True`, chama o backend real e grava."""

    def __init__(self, pasta: Path, real: ChatBackend | None = None, gravar: bool = False) -> None:
        self.pasta = pasta
        self.real = real
        self.gravar = gravar

    def chat(
        self, messages: Sequence[Message], *, modelo: str, json_mode: bool, no: str
    ) -> LLMResult:
        chave = fixture_key(no, modelo, messages, json_mode)
        arquivo = self.pasta / f"{chave}.json"
        if arquivo.exists():
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            return LLMResult(
                texto=dados["texto"],
                tokens_entrada=dados.get("tokens_entrada", 0),
                tokens_saida=dados.get("tokens_saida", 0),
                modelo=modelo,
            )
        if not (self.gravar and self.real):
            raise MissingFixture(f"Sem resposta gravada para '{chave}' em {self.pasta}")
        resultado = self.real.chat(messages, modelo=modelo, json_mode=json_mode, no=no)
        self.pasta.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(
            json.dumps(
                {
                    "texto": resultado.texto,
                    "tokens_entrada": resultado.tokens_entrada,
                    "tokens_saida": resultado.tokens_saida,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return resultado


@dataclass
class ScriptedBackend:
    """Backend de teste: devolve respostas na ordem, por nó do grafo."""

    respostas: dict[str, list[str]] = field(default_factory=dict)
    chamadas: list[tuple[str, list[Message]]] = field(default_factory=list)

    def add(self, no: str, resposta: str | BaseModel | dict[str, Any]) -> None:
        if isinstance(resposta, BaseModel):
            texto = resposta.model_dump_json()
        elif isinstance(resposta, dict):
            texto = json.dumps(resposta, ensure_ascii=False)
        else:
            texto = resposta
        self.respostas.setdefault(no, []).append(texto)

    def chat(
        self, messages: Sequence[Message], *, modelo: str, json_mode: bool, no: str
    ) -> LLMResult:
        self.chamadas.append((no, list(messages)))
        fila = self.respostas.get(no)
        if not fila:
            raise MissingFixture(f"ScriptedBackend sem resposta para o nó '{no}'")
        texto = fila.pop(0) if len(fila) > 1 else fila[0]
        return LLMResult(texto=texto, tokens_entrada=100, tokens_saida=50, modelo=modelo)


UsageHook = Callable[[str, LLMResult], None]


class LLM:
    """Fachada usada pelos agentes: saída estruturada, orçamento e registro de uso."""

    def __init__(self, backend: ChatBackend, settings: Settings) -> None:
        self.backend = backend
        self.settings = settings

    def chat(
        self,
        messages: Sequence[Message],
        *,
        no: str,
        modelo: str | None = None,
        json_mode: bool = False,
        tokens_usados: int = 0,
        on_usage: UsageHook | None = None,
    ) -> LLMResult:
        limite = self.settings.llm_max_tokens_per_session
        if limite and tokens_usados >= limite:
            raise TokenBudgetExceeded(
                f"Limite de {limite} tokens da sessão atingido; novas chamadas ao LLM estão "
                "bloqueadas."
            )
        modelo = modelo or self.settings.llm_model_text
        resultado = self.backend.chat(messages, modelo=modelo, json_mode=json_mode, no=no)
        log_event(
            logger,
            "llm.chamada",
            no=no,
            modelo=modelo,
            tokens_entrada=resultado.tokens_entrada,
            tokens_saida=resultado.tokens_saida,
            latencia_ms=resultado.latencia_ms,
            resultado="ok",
        )
        if on_usage:
            on_usage(no, resultado)
        return resultado

    def structured[T: BaseModel](
        self,
        messages: Sequence[Message],
        schema: type[T],
        *,
        no: str,
        modelo: str | None = None,
        tokens_usados: int = 0,
        on_usage: UsageHook | None = None,
        tentativas_reparo: int = 1,
    ) -> T:
        """Pede JSON e valida com o esquema; se falhar, devolve o erro ao LLM para reparar."""
        msgs = list(messages)
        usados = tokens_usados
        for tentativa in range(tentativas_reparo + 1):
            res = self.chat(
                msgs, no=no, modelo=modelo, json_mode=True, tokens_usados=usados, on_usage=on_usage
            )
            usados += res.tokens
            try:
                return schema.model_validate_json(extract_json(res.texto))
            except (ValidationError, ValueError) as exc:
                if tentativa >= tentativas_reparo:
                    raise LLMError(
                        f"Resposta do LLM fora do esquema {schema.__name__}: {exc}"
                    ) from exc
                msgs = [
                    *msgs,
                    {"role": "assistant", "content": res.texto},
                    {
                        "role": "user",
                        "content": (
                            "A resposta anterior não segue o esquema JSON pedido. Erro:\n"
                            f"{str(exc)[:1500]}\nResponda de novo, só com o JSON corrigido."
                        ),
                    },
                ]
        raise AssertionError("inalcançável")


def extract_json(texto: str) -> str:
    """Tira cercas ```json``` e texto em volta do objeto JSON."""
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    inicio, fim = t.find("{"), t.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError("Nenhum objeto JSON na resposta")
    return t[inicio : fim + 1]


def build_llm(settings: Settings) -> LLM:
    backend: ChatBackend
    if settings.llm_mode == "replay":
        backend = ReplayBackend(settings.llm_fixtures_dir)
    elif settings.llm_mode == "record":
        backend = ReplayBackend(settings.llm_fixtures_dir, DashScopeBackend(settings), gravar=True)
    else:
        backend = DashScopeBackend(settings)
    return LLM(backend, settings)

"""Configuração lida só de variáveis de ambiente (plano §2.3, spec §16)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM (DashScope, API compatível com OpenAI)
    dashscope_api_key: SecretStr = SecretStr("")
    dashscope_base_url: str = (
        "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    )
    llm_model_text: str = "qwen3.8-max"
    llm_model_vision: str = "qwen3.8-max"
    llm_model_judge: str = "deepseek-v4.1-flash-1017"
    # Transcrições longas (≈7 KB) levam mais de 60 s na interpretação (medido em 2026-11-09).
    llm_timeout_seconds: float = 180.0
    llm_max_retries: int = 3
    llm_max_tokens_per_session: int = 400_000
    llm_temperature: float | None = None
    # Modo de raciocínio dos modelos Qwen3 (enable_thinking). Ligado, a extração leva
    # ~10x mais tempo e tokens (medido em 2026-11-08: 203 s contra 19 s).
    llm_enable_thinking: bool = False
    # "dashscope" chama a API; "replay" usa respostas gravadas (testes N1/N2).
    llm_mode: str = "dashscope"
    llm_fixtures_dir: Path = Path("tests/fixtures/llm")

    # Serviços
    agent_archimate_url: str = "http://agent-archimate:8000"
    tool_archi_url: str = "http://tool-archi:8000"
    tool_archi_timeout_seconds: float = 180.0

    # Pastas
    sessions_dir: Path = Path("data/sessions")
    kb_dir: Path = Path("kb")

    log_level: str = Field(default="INFO")
    service_name: str = "archagent"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

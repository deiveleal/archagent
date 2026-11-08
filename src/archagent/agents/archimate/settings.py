"""Configuração própria do agente ArchiMate (além da do núcleo)."""

from __future__ import annotations

from archagent.core.config import Settings


class ArchimateSettings(Settings):
    # Enquanto as fichas do vault não forem revisadas pelo arquiteto, os rascunhos
    # podem ser usados em desenvolvimento e na avaliação (pendência P-12).
    vault_incluir_rascunhos: bool = False
    max_rodadas_correcao: int = 3
    max_perguntas_por_rodada: int = 5

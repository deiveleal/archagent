"""Juiz LLM (docs/harness.md §5.4): modelo diferente do agente, rubrica fechada sim/não."""

from __future__ import annotations

from pydantic import BaseModel

from archagent.agents.archimate import prompts
from archagent.agents.archimate.settings import ArchimateSettings
from archagent.core.llm import LLM, build_llm


class RubricaAlternativa(BaseModel):
    tem_pros: bool
    tem_contras: bool
    cita_impacto: bool
    aponta_conflitos: bool

    @property
    def aprovada(self) -> bool:
        return all((self.tem_pros, self.tem_contras, self.cita_impacto, self.aponta_conflitos))


def juiz(settings: ArchimateSettings) -> LLM:
    return build_llm(settings.model_copy(update={"llm_temperature": 0.0}))


def julgar_alternativa(llm: LLM, settings: ArchimateSettings, proposta: str,
                       resposta: str) -> RubricaAlternativa:  # fmt: skip
    msgs = [
        {"role": "system", "content": prompts.JUIZ_ALTERNATIVA},
        {"role": "user", "content": f"Alternativa proposta:\n{proposta}\n\n"
                                    f"Resposta do assistente:\n{resposta}"},
    ]  # fmt: skip
    return llm.structured(msgs, RubricaAlternativa, no="juiz", modelo=settings.llm_model_judge)

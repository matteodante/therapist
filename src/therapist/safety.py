"""Deterministic routing for explicit safety disclosures, not risk prediction."""

from dataclasses import dataclass
from enum import StrEnum


class SafetyState(StrEnum):
    CLEAR = "clear"
    SAFETY_CONCERN = "safety_concern"
    IMMEDIATE_DANGER_DISCLOSED = "immediate_danger_disclosed"


@dataclass(frozen=True)
class CrisisResource:
    emergency: str
    crisis_line: str | None


@dataclass(frozen=True)
class SafetyAssessment:
    state: SafetyState
    resource: CrisisResource | None


_CONCERN = (
    "farmi del male",
    "farla finita",
    "non voglio vivere",
    "uccidermi",
    "suicid",
    "hurt myself",
    "kill myself",
    "end my life",
    "don't want to live",
    "do not want to live",
)
_IMMEDIATE = (
    "adesso",
    "ora",
    "subito",
    "ho un piano",
    "ho già un piano",
    "right now",
    "tonight",
    "i have a plan",
    "already have a plan",
)


class SafetyController:
    def assess(self, text: str, locale: str) -> SafetyAssessment:
        normalized = " ".join(text.casefold().split())
        if not any(term in normalized for term in _CONCERN):
            return SafetyAssessment(SafetyState.CLEAR, None)
        resource = _resource(locale)
        state = (
            SafetyState.IMMEDIATE_DANGER_DISCLOSED
            if any(term in normalized for term in _IMMEDIATE)
            else SafetyState.SAFETY_CONCERN
        )
        return SafetyAssessment(state, resource)


def crisis_message(assessment: SafetyAssessment, locale: str) -> str:
    resource = assessment.resource
    if resource is None:
        return ""
    if locale.casefold().startswith("it"):
        urgency = (
            "Chiama subito il 112 o vai al pronto soccorso più vicino. "
            if assessment.state is SafetyState.IMMEDIATE_DANGER_DISCLOSED
            else "Se pensi di poter agire, chiama il 112. "
        )
        return (
            "Quello che hai scritto merita attenzione immediata. "
            "Se puoi, allontana ciò che potresti usare per farti male e raggiungi una persona "
            f"fisicamente presente. {urgency}"
            "Io sono un'AI: non posso monitorarti, localizzarti o contattare i soccorsi. "
            "Sei in pericolo immediato in questo momento?"
        )
    urgency = (
        "Call 911 now or go to the nearest emergency department. "
        if assessment.state is SafetyState.IMMEDIATE_DANGER_DISCLOSED
        else "If you may act, call 911 or call/text 988. "
    )
    return (
        "What you wrote needs immediate attention. If you can, move away from anything you "
        f"could use to hurt yourself and reach someone physically present. {urgency}"
        "I am an AI and cannot monitor you, locate you, or contact emergency services. "
        "Are you in immediate danger right now?"
    )


def _resource(locale: str) -> CrisisResource:
    if locale.casefold().startswith("it"):
        return CrisisResource("112", None)
    return CrisisResource("911", "988")


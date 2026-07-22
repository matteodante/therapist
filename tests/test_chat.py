from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from therapist.chat import ChatSession, TherapistReply
from therapist.memory import (
    CaseFormulation,
    MemoryKind,
    MemoryObservation,
    MemoryStatus,
    MemoryStore,
)
from therapist.protocol import ProtocolPack
from therapist.safety import SafetyState

models.ALLOW_MODEL_REQUESTS = False


def _pack() -> ProtocolPack:
    return ProtocolPack.load(Path("protocols/transdiagnostic-v0.3.0"))


def test_normal_turn_returns_reply_and_persists_supported_observation(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = ChatSession(
        TestModel(
            custom_output_args={
                "reply": "Sono qui. Cosa succede al lavoro?",
                "observations": [
                    {"kind": "event", "content": "The user feels pressure at work."}
                ],
                "confirmed_memory_ids": [],
                "proposed_focus": None,
            }
        ),
        _pack(),
        store,
        "it-IT",
    )

    turn = session.respond("Mi sento sotto pressione al lavoro.")

    assert turn.safety_state is SafetyState.CLEAR
    assert turn.text == "Sono qui. Cosa succede al lavoro?"
    assert store.load_session_history(store.active_session().id)  # type: ignore[union-attr]
    assert store.list_memory()[0].status is MemoryStatus.USER_CONFIRMED


def test_expired_session_is_closed_before_a_new_turn(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    model = TestModel(
        custom_output_args={"reply": "Bentornato.", "observations": [], "proposed_focus": None}
    )
    session = ChatSession(model, _pack(), store, "it-IT")
    january = datetime(2026, 1, 1, tzinfo=UTC)

    session.respond("A gennaio ero preoccupato per il lavoro.", january)
    old_id = store.active_session().id  # type: ignore[union-attr]
    session.respond("Sono passati alcuni mesi.", january + timedelta(days=90))

    assert store.active_session().id != old_id  # type: ignore[union-attr]
    assert store.list_sessions()[1].ended_at is not None


def test_end_consolidates_session_and_revises_formulation(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    store.save_turn(active, "Sono teso al lavoro.", "Cosa accade?", [])
    formulation = CaseFormulation(
        presenting_concerns=["Work stress"], current_focus="Understand work pressure"
    )
    model = TestModel(
        custom_output_args={
            "summary": "The user explored work pressure.",
            "themes": ["work"],
            "interventions": [],
            "user_response": "The user identified tension.",
            "open_questions": ["What triggers it?"],
            "formulation": formulation.model_dump(),
        }
    )

    closed = ChatSession(model, _pack(), store, "it-IT").end()

    assert closed is not None
    assert closed.summary == "The user explored work pressure."
    assert store.load_formulation().current_focus == "Understand work pressure"


def test_crisis_turn_bypasses_model_and_archives_the_exchange(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = ChatSession(
        TestModel(custom_output_text="THIS MUST NOT APPEAR"), _pack(), store, "it-IT"
    )

    turn = session.respond("Voglio uccidermi adesso, ho un piano.")

    assert turn.safety_state is SafetyState.IMMEDIATE_DANGER_DISCLOSED
    assert "112" in turn.text
    assert "contattare i soccorsi" in turn.text.casefold()
    assert "THIS MUST NOT APPEAR" not in turn.text
    assert "uccidermi" in store.session_transcript(store.active_session().id)  # type: ignore[union-attr]


def test_explicit_user_confirmation_promotes_existing_hypothesis(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    confirmed_at = datetime(2026, 4, 5, 12, tzinfo=UTC)
    active = store.start_session(confirmed_at - timedelta(minutes=10))
    evidence_id = store.save_turn(
        active,
        "I avoid calls",
        "Could this be fear?",
        [],
        confirmed_at - timedelta(minutes=10),
    )
    hypothesis = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.PATTERN,
                content="Fear may maintain call avoidance.",
            )
        ],
        evidence_id,
    )[0]
    model = TestModel(
        custom_output_args={
            "reply": "That confirmation helps us refine the picture.",
            "observations": [],
            "confirmed_memory_ids": [hypothesis.id],
            "proposed_focus": None,
        }
    )

    ChatSession(model, _pack(), store, "en-US").respond(
        "Yes, that pattern fits exactly.", confirmed_at
    )

    confirmed = store.list_memory()[0]
    assert confirmed.status is MemoryStatus.USER_CONFIRMED
    assert confirmed.last_seen_at == confirmed_at.isoformat()


def test_therapeutic_reply_rejects_interrogation() -> None:
    with pytest.raises(ValidationError, match="at most one question"):
        TherapistReply(reply="What happened? And what did you feel?")

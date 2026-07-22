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
    return ProtocolPack.load(Path("protocols/transdiagnostic-v0.4.0"))


def test_normal_turn_returns_reply_and_persists_supported_observation(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = ChatSession(
        TestModel(
            custom_output_args={
                "reply": "Sono qui. Cosa succede al lavoro?",
                "observations": [
                    {
                        "kind": "event",
                        "content": "The user feels pressure at work.",
                        "evidence_quote": "sotto pressione al lavoro",
                        "aliases": ["work stress", "pressione lavorativa"],
                    }
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
    assert store.list_sessions()[1].consolidation_error == "UnexpectedModelBehavior"


def test_end_consolidates_session_and_revises_formulation(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    message_id = store.save_turn(active, "Sono teso al lavoro.", "Cosa accade?", [])
    claim = store.add_observations(
        [MemoryObservation(kind=MemoryKind.EVENT, content="Work stress")], message_id
    )[0]
    store.save_formulation(CaseFormulation(current_focus="Understand work pressure"))
    model = TestModel(
        custom_output_args={
            "summary": "The user explored work pressure.",
            "themes": ["work"],
            "interventions": [],
            "user_response": "The user identified tension.",
            "open_questions": ["What triggers it?"],
            "formulation_links": {"presenting_concerns": [claim.id]},
        }
    )

    closed = ChatSession(model, _pack(), store, "it-IT").end()

    assert closed is not None
    assert closed.summary == "The user explored work pressure."
    assert store.load_formulation().current_focus == "Understand work pressure"
    assert store.load_formulation().evidence == {"presenting_concerns": [claim.id]}


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
            "confirmation_evidence_quote": "that pattern fits exactly",
            "proposed_focus": None,
        }
    )

    ChatSession(model, _pack(), store, "en-US").respond(
        "Yes, that pattern fits exactly.", confirmed_at
    )

    confirmed = store.list_memory()[0]
    assert confirmed.status is MemoryStatus.USER_CONFIRMED
    assert confirmed.last_seen_at == confirmed_at.isoformat()


def test_offered_hypothesis_becomes_pending_and_is_cleared_on_confirmation(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    offered = TestModel(
        custom_output_args={
            "reply": "Could avoidance be protecting you from anticipated criticism?",
            "observations": [],
            "offered_hypothesis": "Avoidance may protect against anticipated criticism.",
            "process_stage": "formulate",
            "selected_skill": "build-shared-formulation",
        }
    )
    ChatSession(offered, _pack(), store, "en-US").respond(
        "I put off calls when I expect criticism."
    )
    pending_id = store.load_app_state().pending_hypothesis_id
    assert pending_id is not None

    confirmed = TestModel(
        custom_output_args={
            "reply": "That gives us a shared working explanation.",
            "observations": [],
            "confirmed_memory_ids": [pending_id],
            "confirmation_evidence_quote": "that pattern fits",
            "process_stage": "formulate",
            "selected_skill": "build-shared-formulation",
        }
    )
    ChatSession(confirmed, _pack(), store, "en-US").respond(
        "Yes, that pattern fits exactly."
    )

    assert store.load_app_state().pending_hypothesis_id is None
    assert store.list_memory()[0].status is MemoryStatus.USER_CONFIRMED


def test_therapeutic_reply_allows_natural_question_count() -> None:
    assert TherapistReply(reply="That sounds painful.").reply == "That sounds painful."
    assert TherapistReply(
        reply="What happened just before it? What did you notice in your body?"
    ).reply.endswith("body?")


def test_therapeutic_reply_limits_durable_memory_writes() -> None:
    with pytest.raises(ValidationError, match="at most 2 items"):
        TherapistReply(
            reply="Tell me more.",
            observations=[
                {"kind": "fact", "content": f"Fact {index}"} for index in range(3)
            ],
        )


def test_unsupported_direct_observation_does_not_become_memory(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    model = TestModel(
        custom_output_args={
            "reply": "Tell me more.",
            "observations": [
                {
                    "kind": "fact",
                    "content": "The user has two children.",
                    "evidence_quote": "two children",
                }
            ],
        }
    )

    ChatSession(model, _pack(), store, "en-US").respond("Work was difficult today.")

    assert store.list_memory() == []


def test_natural_correction_replaces_existing_memory_without_duplicate(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    evidence_id = store.save_turn(
        active,
        "Mia madre vive sola.",
        "Capisco.",
        [],
    )
    old = store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="La madre vive sola.")],
        evidence_id,
    )[0]
    model = TestModel(
        custom_output_args={
            "reply": "Grazie della correzione: aggiorno il quadro.",
            "observations": [],
            "corrections": [
                {
                    "memory_id": old.id,
                    "replacement": "La madre vive con la zia quasi tutta la settimana.",
                    "evidence_quote": (
                        "Devo correggere una cosa: mia madre non vive sola; vive con mia zia "
                        "quasi tutta la settimana."
                    ),
                }
            ],
        }
    )

    ChatSession(model, _pack(), store, "it-IT").respond(
        "Devo correggere una cosa: mia madre non vive sola; vive con mia zia quasi tutta "
        "la settimana."
    )

    items = store.list_memory()
    assert len(items) == 1
    assert items[0].id == old.id
    assert items[0].status is MemoryStatus.USER_CORRECTED
    assert items[0].content == "La madre vive con la zia quasi tutta la settimana."
    assert "vive sola" not in store.working_context("madre zia").model_dump_json()


def test_focus_and_intervention_require_user_evidence_and_persist(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    offered = TestModel(
        custom_output_args={
            "reply": "Would a two-minute draft be worth testing?",
            "observations": [],
            "proposed_focus": "Reduce avoidance around drafting",
            "process_stage": "intervene",
            "selected_skill": "change-avoidance-behavior",
            "intervention": {
                "skill": "change-avoidance-behavior",
                "description": "Write a two-minute draft",
                "prediction": "Anxiety may rise without preventing a start",
                "state": "offered",
            },
        }
    )
    ChatSession(offered, _pack(), store, "en-US").respond(
        "I keep postponing the first draft."
    )
    intervention = store.list_interventions()[0]

    accepted = TestModel(
        custom_output_args={
            "reply": "Good—we can treat it as a small experiment.",
            "observations": [],
            "accepted_focus": "reducing that avoidance",
            "focus_evidence_quote": "focus on reducing that avoidance",
            "process_stage": "intervene",
            "selected_skill": "change-avoidance-behavior",
            "intervention": {
                "record_id": intervention.id,
                "skill": "change-avoidance-behavior",
                "description": intervention.description,
                "state": "agreed",
                "evidence_quote": "I agree to try the two-minute draft",
            },
        }
    )
    ChatSession(accepted, _pack(), store, "en-US").respond(
        "I agree to try the two-minute draft; let's focus on reducing that avoidance."
    )

    assert store.load_formulation().current_focus == "reducing that avoidance"
    assert len(store.list_interventions()) == 1
    assert store.list_interventions()[0].state.value == "agreed"
    assert store.load_app_state().pending_intervention_id == intervention.id


def test_unaccepted_proposed_focus_expires_when_session_ends(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.save_formulation(CaseFormulation(proposed_focus="Old proposed focus"))
    active = store.start_session()
    store.save_turn(active, "I am still exploring.", "Take your time.", [])
    model = TestModel(
        custom_output_args={
            "summary": "The session remained exploratory.",
            "themes": [],
            "interventions": [],
            "user_response": "",
            "open_questions": [],
            "formulation_links": {},
        }
    )

    ChatSession(model, _pack(), store, "en-US").end()

    assert store.load_formulation().proposed_focus is None


def test_misattunement_forces_repair_before_another_technique(tmp_path: Path) -> None:
    model = TestModel(
        custom_output_args={
            "reply": "Hai ragione: sono passato ai consigli senza capire. Cosa ho perso?",
            "observations": [
                {
                    "kind": "preference",
                    "content": "The user wants understanding before advice.",
                    "evidence_quote": "non hai capito e mi stai dando troppi consigli",
                }
            ],
            "process_stage": "repair",
            "selected_skill": "repair-misattunement",
        }
    )

    turn = ChatSession(model, _pack(), MemoryStore(tmp_path), "it-IT").respond(
        "Non hai capito e mi stai dando troppi consigli."
    )

    assert turn.process_stage.value == "repair"
    assert turn.selected_skill.value == "repair-misattunement"  # type: ignore[union-attr]

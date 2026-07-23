import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from therapist.memory import (
    CaseFormulation,
    InterventionState,
    MemoryError,
    MemoryKind,
    MemoryObservation,
    MemoryStatus,
    MemoryStore,
    _lexical_score,
)


def test_memory_round_trip_never_writes_plaintext(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(
        session, "A very private detail", "I am listening", [], datetime(2026, 1, 1, tzinfo=UTC)
    )
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.EVENT, content="Work stress")], message_id
    )
    store.save_formulation(CaseFormulation(presenting_concerns=["Work stress"]))

    assert "A very private detail" in store.session_transcript(session.id)
    assert store.list_memory()[0].content == "Work stress"
    database = (tmp_path / "thera.db").read_bytes()
    assert b"A very private detail" not in database
    assert b"Work stress" not in database
    assert (tmp_path / "memory.key").stat().st_mode & 0o777 == 0o600


def test_hypotheses_require_confirmation_and_corrections_override_derived_text(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "I always avoid Marco", "You wonder why.", [])
    item = store.add_observations(
        [MemoryObservation(kind=MemoryKind.PATTERN, content="The user always avoids Marco")],
        message_id,
    )[0]
    store.save_formulation(CaseFormulation(relationship_patterns=["The user always avoids Marco"]))
    store.close_session(session, summary="The user always avoids Marco")

    assert item.status is MemoryStatus.AGENT_HYPOTHESIS
    corrected = store.correct_memory(item.id, "The user sometimes avoids Marco")
    context = store.working_context("Marco").model_dump_json()

    assert corrected.status is MemoryStatus.USER_CORRECTED
    assert "always avoids" not in context
    assert "sometimes avoids" in context


def test_confirming_hypothesis_clears_tentative_formulation_and_pending_state(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "I may avoid criticism", "Does that fit?", [])
    item = store.add_observations(
        [MemoryObservation(kind=MemoryKind.HYPOTHESIS, content="Criticism may trigger avoidance")],
        message_id,
    )[0]
    store.save_formulation_links({"open_hypotheses": [item.id]})
    app_state = store.load_app_state()
    app_state.pending_hypothesis_id = item.id
    store.save_app_state(app_state)

    store.confirm_memory(item.id)

    assert store.load_formulation().open_hypotheses == []
    assert store.load_formulation().evidence == {}
    assert store.load_app_state().pending_hypothesis_id is None


def test_forgetting_suppresses_active_context_but_remains_in_export(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "I moved to Turin", "How is Turin?", [])
    item = store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="The user moved to Turin")], message_id
    )[0]

    archived = store.forget_memory(item.id)

    assert archived.status is MemoryStatus.ARCHIVED
    assert store.list_memory() == []
    assert store.working_context("Turin").relevant_excerpts == []
    assert store.export()["memory"][0]["status"] == "archived"


def test_forgetting_invalidates_paraphrased_derived_summary(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(
        session,
        "My private project called Cedar made me anxious.",
        "What felt difficult?",
        [],
    )
    item = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.EVENT,
                content="Private project Cedar caused anxiety last spring.",
            )
        ],
        message_id,
    )[0]
    store.close_session(session, summary="The user discussed anxiety about project Cedar.")

    store.forget_memory(item.id)

    assert "Cedar" not in store.working_context("project Cedar").model_dump_json()


def test_forgetting_removes_focus_and_intervention_derived_from_claim(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(
        session,
        "Project Cedar makes me anxious and work is difficult.",
        "I hear you.",
        [],
    )
    cedar, work = store.add_observations(
        [
            MemoryObservation(kind=MemoryKind.EVENT, content="Project Cedar causes anxiety"),
            MemoryObservation(kind=MemoryKind.EVENT, content="Work is difficult"),
        ],
        message_id,
    )
    store.save_formulation_links(
        {"presenting_concerns": [cedar.id, work.id]},
        current_focus="Understand Project Cedar anxiety",
    )
    store.create_intervention(
        skill="build-shared-formulation",
        description="Write about Project Cedar",
        prediction=None,
        state=InterventionState.AGREED,
        linked_memory_ids=[cedar.id],
        evidence_message_id=message_id,
    )

    store.forget_memory(cedar.id)

    context = store.working_context("Cedar").model_dump_json()
    assert "Cedar" not in context
    assert cedar.id not in context
    assert store.load_formulation().presenting_concerns == ["Work is difficult"]
    retained = store.list_interventions()[0]
    assert retained.state is InterventionState.STOPPED
    assert retained.description == "Content removed by user request."
    assert cedar.id not in retained.linked_memory_ids


def test_correction_rolls_back_if_derived_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "I live in Turin", "Noted", [])
    item = store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="The user lives in Turin")],
        message_id,
    )[0]

    def fail_cleanup(*_: object, **__: object) -> None:
        raise RuntimeError("simulated cleanup failure")

    monkeypatch.setattr(store, "_replace_derived_text", fail_cleanup)

    with pytest.raises(RuntimeError, match="simulated cleanup failure"):
        store.correct_memory(item.id, "The user lives in Milan")

    persisted = store.list_memory()[0]
    assert persisted.content == "The user lives in Turin"
    assert persisted.status is MemoryStatus.USER_CONFIRMED


def test_session_gap_and_context_are_bounded(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    started = datetime(2026, 1, 1, tzinfo=UTC)
    session = store.start_session(started)
    for index in range(250):
        store.save_turn(
            session,
            f"Archive message {index} about recurring work pressure",
            "Tell me more.",
            [],
            started + timedelta(minutes=index),
        )

    assert store.session_expired(session, started + timedelta(hours=13))
    assert len(store.working_context("work pressure").relevant_excerpts) == 5
    assert store.working_context("work pressure").relevant_excerpts == [
        f"Archive message {index} about recurring work pressure" for index in range(249, 244, -1)
    ]


def test_session_activity_survives_process_restart(tmp_path: Path) -> None:
    started = datetime(2026, 1, 1, tzinfo=UTC)
    store = MemoryStore(tmp_path)
    session = store.start_session(started)
    store.save_turn(
        session,
        "Still talking",
        "I am here",
        [],
        started + timedelta(hours=7),
    )

    restarted = MemoryStore(tmp_path)
    restored = restarted.active_session()

    assert restored is not None
    assert restored.last_activity_at == (started + timedelta(hours=7)).isoformat()
    assert not restarted.session_expired(restored, started + timedelta(hours=14))


class MeaningEmbedder:
    def __init__(self) -> None:
        self.document_calls: list[list[str]] = []

    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.casefold()
        if any(term in lowered for term in ("calls", "telephone", "appointments")):
            return [1.0, 0.0]
        return [0.0, 1.0]

    def embed_documents_sync(self, documents: list[str]) -> SimpleNamespace:
        self.document_calls.append(documents)
        return SimpleNamespace(embeddings=[self._vector(text) for text in documents])

    def embed_query_sync(self, query: str) -> SimpleNamespace:
        return SimpleNamespace(embeddings=[self._vector(query)])


def test_semantic_index_ranks_meaning_and_is_encrypted_and_rebuildable(
    tmp_path: Path,
) -> None:
    embedder = MeaningEmbedder()
    store = MemoryStore(  # type: ignore[arg-type]
        tmp_path, embedding_model="test:meaning", embedder=embedder
    )
    january = datetime(2026, 1, 1, tzinfo=UTC)
    session = store.start_session(january)
    old_message = store.save_turn(
        session, "I postpone telephone appointments", "Tell me more", [], january
    )
    calls = store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="Telephone appointments are postponed")],
        old_message,
        january,
    )[0]
    new_message = store.save_turn(
        session,
        "I enjoy my garden",
        "What do you enjoy?",
        [],
        january + timedelta(days=120),
    )
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="The garden feels restorative")],
        new_message,
        january + timedelta(days=120),
    )

    context = store.working_context("telephone appointments")

    assert context.confirmed_memory[0].id == calls.id
    assert len(embedder.document_calls) == 2
    database_bytes = store.database_path.read_bytes()
    assert b"Telephone appointments" not in database_bytes
    assert b"[1.0,0.0]" not in database_bytes

    restarted = MemoryStore(  # type: ignore[arg-type]
        tmp_path, embedding_model="test:meaning", embedder=embedder
    )
    assert restarted.working_context("telephone appointments").confirmed_memory[0].id == calls.id
    assert len(embedder.document_calls) == 2

    restarted.correct_memory(calls.id, "Telephone appointments are now manageable")
    restarted.working_context("appointments")
    assert len(embedder.document_calls) == 3

    restarted.forget_memory(calls.id)
    with sqlite3.connect(restarted.database_path) as database:
        remaining = database.execute(
            "SELECT COUNT(*) FROM semantic_index WHERE entity_type = 'memory' AND entity_id = ?",
            (calls.id,),
        ).fetchone()[0]
    assert remaining == 0


def test_semantic_archive_and_intervention_retrieval_crosses_languages(
    tmp_path: Path,
) -> None:
    embedder = MeaningEmbedder()
    store = MemoryStore(  # type: ignore[arg-type]
        tmp_path, embedding_model="test:meaning", embedder=embedder
    )
    session = store.start_session(datetime(2026, 1, 1, tzinfo=UTC))
    call_message = store.save_turn(
        session,
        "I postpone difficult calls with my manager.",
        "I hear you.",
        [],
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    garden_message = store.save_turn(
        session,
        "Gardening feels restful.",
        "Noted.",
        [],
        datetime(2026, 2, 1, tzinfo=UTC),
    )
    call_intervention = store.create_intervention(
        skill="problem-solving",
        description="Prepare one difficult telephone appointment.",
        prediction=None,
        state=InterventionState.OFFERED,
        linked_memory_ids=[],
        evidence_message_id=call_message,
    )
    store.create_intervention(
        skill="behavioral-change",
        description="Spend ten minutes in the garden.",
        prediction=None,
        state=InterventionState.OFFERED,
        linked_memory_ids=[],
        evidence_message_id=garden_message,
    )

    context = store.working_context("telephone appointments")

    assert context.relevant_excerpts[0].startswith("I postpone difficult calls")
    assert context.active_interventions[0].id == call_intervention.id


def test_lexical_tokens_support_cjk_and_thai_without_spaces() -> None:
    assert _lexical_score("上司への電話を延期する", "上司との電話が怖い") > 0
    assert _lexical_score("เลื่อนการโทรหาหัวหน้า", "กลัวการโทรหาหัวหน้า") > 0


def test_semantic_failure_fails_closed_instead_of_silently_using_lexical(
    tmp_path: Path,
) -> None:
    class FailingEmbedder:
        def embed_documents_sync(self, documents: list[str]) -> SimpleNamespace:
            raise RuntimeError("local model unavailable")

        def embed_query_sync(self, query: str) -> SimpleNamespace:
            raise RuntimeError("local model unavailable")

    store = MemoryStore(  # type: ignore[arg-type]
        tmp_path, embedding_model="test:failing", embedder=FailingEmbedder()
    )
    session = store.start_session()
    message_id = store.save_turn(session, "Calls cause pressure", "I hear you", [])
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="Calls cause pressure")],
        message_id,
    )
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="Gardening feels restful")],
        message_id + 1,
    )

    with pytest.raises(MemoryError, match="Run `thera setup`"):
        store.working_context("calls pressure")


def test_explicit_merge_target_wins_over_earlier_near_duplicate(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "Calls are hard", "I hear you", [])
    first, target = store.add_observations(
        [
            MemoryObservation(kind=MemoryKind.FACT, content="Calls are very difficult"),
            MemoryObservation(kind=MemoryKind.FACT, content="Calls feel difficult"),
        ],
        message_id,
    )

    updated = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.FACT,
                content="Calls are very difficult",
                merge_into_id=target.id,
            )
        ],
        message_id + 1,
    )[0]

    assert updated.id == target.id
    assert updated.id != first.id


def test_observation_uses_the_session_timestamp(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    occurred_at = datetime(2025, 2, 3, 10, tzinfo=UTC)
    session = store.start_session(occurred_at)
    message_id = store.save_turn(session, "Historical event", "Tell me more.", [], occurred_at)

    item = store.add_observations(
        [MemoryObservation(kind=MemoryKind.EVENT, content="A historical event occurred.")],
        message_id,
        occurred_at,
    )[0]

    assert item.first_seen_at == occurred_at.isoformat()
    assert item.last_seen_at == occurred_at.isoformat()


def test_near_duplicate_memory_merges_but_distinct_numbers_do_not(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    first_id = store.save_turn(session, "First", "Reply", [])
    first = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.HYPOTHESIS,
                content="Avoidance may protect against anticipated criticism.",
            )
        ],
        first_id,
    )[0]
    second_id = store.save_turn(session, "Second", "Reply", [])
    merged = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.HYPOTHESIS,
                content="Avoidance may protect them against anticipated criticism.",
                merge_into_id=first.id,
            ),
            MemoryObservation(kind=MemoryKind.EVENT, content="Completed 2 visits"),
            MemoryObservation(kind=MemoryKind.EVENT, content="Completed 6 visits"),
        ],
        second_id,
    )

    assert merged[0].id == first.id
    assert len(store.list_memory()) == 3


def test_near_duplicate_memory_never_merges_opposite_negation(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    first_id = store.save_turn(session, "First", "Reply", [])
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="The mother lives alone")],
        first_id,
    )
    second_id = store.save_turn(session, "Correction", "Reply", [])
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="The mother does not live alone")],
        second_id,
    )

    assert len(store.list_memory()) == 2


def test_delete_all_clears_archive_memory_and_formulation(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "Private", "Reply", [])
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.EVENT, content="Private event")], message_id
    )
    store.save_formulation(CaseFormulation(presenting_concerns=["Private event"]))

    store.delete_all()

    assert store.list_sessions() == []
    assert store.list_memory() == []
    assert store.load_formulation() == CaseFormulation()


def test_legacy_goals_are_migrated_as_historical_events(tmp_path: Path) -> None:
    key = Fernet.generate_key()
    (tmp_path / "memory.key").write_bytes(key)
    cipher = Fernet(key)
    profile = {
        "goals": ["Sleep better"],
        "preferences": {},
        "exercises": [],
        "summary": "",
        "consent_version": "alpha-1",
    }
    with sqlite3.connect(tmp_path / "thera.db") as database:
        database.execute(
            "CREATE TABLE state (name TEXT PRIMARY KEY, payload BLOB NOT NULL, "
            "updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        database.execute(
            "INSERT INTO state(name, payload) VALUES ('profile', ?)",
            (cipher.encrypt(json.dumps(profile).encode()),),
        )

    store = MemoryStore(tmp_path)

    assert store.load_app_state().consent_version == "alpha-1"
    assert store.list_memory()[0].content == "Sleep better"
    assert store.list_memory()[0].kind is MemoryKind.EVENT


def test_formulation_is_derived_from_active_claims_and_tracks_corrections(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "Work calls feel threatening", "Tell me more", [])
    claim = store.add_observations(
        [MemoryObservation(kind=MemoryKind.PATTERN, content="Work calls may trigger avoidance")],
        message_id,
    )[0]

    store.save_formulation_links(
        {
            "maintaining_factors": [claim.id, "invented-id"],
            "open_hypotheses": [claim.id],
        }
    )
    assert store.load_formulation().maintaining_factors == []
    assert store.load_formulation().open_hypotheses == [claim.content]

    store.confirm_memory(claim.id)
    store.save_formulation_links({"maintaining_factors": [claim.id]})
    assert store.load_formulation().maintaining_factors == [claim.content]
    assert store.load_formulation().evidence == {"maintaining_factors": [claim.id]}

    store.correct_memory(claim.id, "Some work calls may trigger avoidance")
    assert store.load_formulation().maintaining_factors == ["Some work calls may trigger avoidance"]

    store.forget_memory(claim.id)
    assert store.load_formulation().maintaining_factors == []
    assert store.load_formulation().evidence == {}


def test_formulation_merge_preserves_omissions_and_supports_explicit_unlink(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "Work is hard", "Tell me more", [])
    old, new = store.add_observations(
        [
            MemoryObservation(kind=MemoryKind.PREFERENCE, content="Listening is preferred"),
            MemoryObservation(kind=MemoryKind.EVENT, content="Work is hard"),
        ],
        message_id,
    )
    store.save_formulation_links({"preferred_help": [old.id]})

    preserved = store.save_formulation_links({"presenting_concerns": [new.id]}, merge_existing=True)
    revised = store.save_formulation_links(
        {},
        merge_existing=True,
        remove_links={"preferred_help": [old.id]},
    )

    assert preserved.evidence == {
        "presenting_concerns": [new.id],
        "preferred_help": [old.id],
    }
    assert revised.evidence == {"presenting_concerns": [new.id]}


def test_intervention_and_alias_retrieval_survive_restart_encrypted(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "I postpone calls with my manager", "I understand", [])
    claim = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.PATTERN,
                content="Avoiding calls brings short-term relief",
                aliases=["manager", "postpone", "work calls"],
            )
        ],
        message_id,
    )[0]
    intervention = store.create_intervention(
        skill="change-avoidance-behavior",
        description="Prepare one sentence and make the call",
        prediction="Anxiety rises briefly",
        state=InterventionState.AGREED,
        linked_memory_ids=[claim.id],
        evidence_message_id=message_id,
    )

    restarted = MemoryStore(tmp_path)
    context = restarted.working_context("talking with my manager")

    assert context.hypotheses[0].id == claim.id
    assert context.active_interventions[0].id == intervention.id
    database = store.database_path.read_bytes()
    assert b"Prepare one sentence" not in database


def test_intervention_can_be_reviewed_and_retried_without_creating_a_copy(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    evidence_id = store.save_turn(session, "I will try a short call", "Agreed", [])
    intervention = store.create_intervention(
        skill="change-avoidance-behavior",
        description="Make a short call",
        prediction="Anxiety may rise",
        state=InterventionState.AGREED,
        linked_memory_ids=[],
        evidence_message_id=evidence_id,
    )

    store.update_intervention(
        intervention.id,
        state=InterventionState.TRIED,
        evidence_message_id=evidence_id,
        outcome="The call was completed",
    )
    reviewed = store.update_intervention(
        intervention.id,
        state=InterventionState.TRIED,
        evidence_message_id=evidence_id,
        user_appraisal="Useful despite anxiety",
    )
    retried = store.update_intervention(
        intervention.id,
        state=InterventionState.AGREED,
        evidence_message_id=evidence_id,
        description="Make another short call",
    )

    assert reviewed.user_appraisal == "Useful despite anxiety"
    assert retried.description == "Make another short call"
    assert retried.state is InterventionState.AGREED
    assert len(store.list_interventions()) == 1


def test_pending_intervention_is_pinned_inside_bounded_context(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    evidence_id = store.save_turn(session, "Try something small", "Agreed", [])
    pending = store.create_intervention(
        skill="change-avoidance-behavior",
        description="Make one short call",
        prediction=None,
        state=InterventionState.OFFERED,
        linked_memory_ids=[],
        evidence_message_id=evidence_id,
    )
    for index in range(6):
        store.create_intervention(
            skill="change-avoidance-behavior",
            description=f"Garden experiment {index}",
            prediction=None,
            state=InterventionState.AGREED,
            linked_memory_ids=[],
            evidence_message_id=evidence_id,
        )
    app_state = store.load_app_state()
    app_state.pending_intervention_id = pending.id
    store.save_app_state(app_state)

    context = store.working_context("garden experiment")

    assert len(context.active_interventions) == 5
    assert context.active_interventions[0].id == pending.id

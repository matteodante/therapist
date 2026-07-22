import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet

from therapist.memory import (
    CaseFormulation,
    InterventionState,
    MemoryKind,
    MemoryObservation,
    MemoryStatus,
    MemoryStore,
)


def test_memory_round_trip_never_writes_plaintext(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(
        session, "Una cosa molto privata", "Ti ascolto", [], datetime(2026, 1, 1, tzinfo=UTC)
    )
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.EVENT, content="Stress da lavoro")], message_id
    )
    store.save_formulation(CaseFormulation(presenting_concerns=["Stress da lavoro"]))

    assert "Una cosa molto privata" in store.session_transcript(session.id)
    assert store.list_memory()[0].content == "Stress da lavoro"
    database = (tmp_path / "thera.db").read_bytes()
    assert b"Una cosa molto privata" not in database
    assert b"Stress da lavoro" not in database
    assert (tmp_path / "memory.key").stat().st_mode & 0o777 == 0o600


def test_hypotheses_require_confirmation_and_corrections_override_derived_text(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "Evito sempre Marco", "Ti chiedi perché.", [])
    item = store.add_observations(
        [MemoryObservation(kind=MemoryKind.PATTERN, content="The user always avoids Marco")],
        message_id,
    )[0]
    store.save_formulation(
        CaseFormulation(relationship_patterns=["The user always avoids Marco"])
    )
    store.close_session(session, summary="The user always avoids Marco")

    assert item.status is MemoryStatus.AGENT_HYPOTHESIS
    corrected = store.correct_memory(item.id, "The user sometimes avoids Marco")
    context = store.working_context("Marco").model_dump_json()

    assert corrected.status is MemoryStatus.USER_CORRECTED
    assert "always avoids" not in context
    assert "sometimes avoids" in context


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

    store.save_formulation_links({"maintaining_factors": [claim.id, "invented-id"]})
    assert store.load_formulation().maintaining_factors == [claim.content]
    assert store.load_formulation().evidence == {"maintaining_factors": [claim.id]}

    store.correct_memory(claim.id, "Some work calls may trigger avoidance")
    assert store.load_formulation().maintaining_factors == [
        "Some work calls may trigger avoidance"
    ]

    store.forget_memory(claim.id)
    assert store.load_formulation().maintaining_factors == []
    assert store.load_formulation().evidence == {}


def test_intervention_and_alias_retrieval_survive_restart_encrypted(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "Rimando le chiamate al capo", "Capisco", [])
    claim = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.PATTERN,
                content="Avoiding calls brings short-term relief",
                aliases=["responsabile", "rimandare", "work calls"],
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
    context = restarted.working_context("parlare con il responsabile")

    assert context.hypotheses[0].id == claim.id
    assert context.active_interventions[0].id == intervention.id
    database = store.database_path.read_bytes()
    assert b"Prepare one sentence" not in database

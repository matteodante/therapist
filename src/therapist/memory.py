"""Encrypted longitudinal memory backed by standard-library SQLite."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field
from pydantic_ai import Embedder, ModelMessage, ModelMessagesTypeAdapter

SESSION_GAP = timedelta(hours=8)
LOCAL_OLLAMA_EMBEDDINGS_URL = "http://localhost:11434/v1"


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


class MemoryKind(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    PATTERN = "pattern"
    HYPOTHESIS = "hypothesis"


class MemoryStatus(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    AGENT_HYPOTHESIS = "agent_hypothesis"
    USER_CORRECTED = "user_corrected"
    ARCHIVED = "archived"


class InterventionState(StrEnum):
    OFFERED = "offered"
    AGREED = "agreed"
    TRIED = "tried"
    NOT_TRIED = "not_tried"
    STOPPED = "stopped"


def valid_intervention_transition(current: InterventionState, target: InterventionState) -> bool:
    allowed = {
        InterventionState.OFFERED: {
            InterventionState.OFFERED,
            InterventionState.AGREED,
            InterventionState.STOPPED,
        },
        InterventionState.AGREED: {
            InterventionState.AGREED,
            InterventionState.TRIED,
            InterventionState.NOT_TRIED,
            InterventionState.STOPPED,
        },
        InterventionState.TRIED: {
            InterventionState.TRIED,
            InterventionState.AGREED,
            InterventionState.STOPPED,
        },
        InterventionState.NOT_TRIED: {
            InterventionState.NOT_TRIED,
            InterventionState.AGREED,
            InterventionState.STOPPED,
        },
    }
    return target in allowed.get(current, set())


class AppState(BaseModel):
    consent_version: str | None = None
    telegram_consent_version: str | None = None
    telegram_update_offset: int | None = Field(default=None, ge=0)
    default_model: str | None = None
    default_locale: str | None = None
    embedding_model: str | None = None
    telegram_allowed_user_id: int | None = Field(default=None, gt=0)
    pending_hypothesis_id: str | None = None
    pending_intervention_id: str | None = None


class CaseFormulation(BaseModel):
    presenting_concerns: list[str] = Field(default_factory=list)
    emotions_and_triggers: list[str] = Field(default_factory=list)
    thoughts_and_behaviors: list[str] = Field(default_factory=list)
    coping_strategies: list[str] = Field(default_factory=list)
    relationship_patterns: list[str] = Field(default_factory=list)
    maintaining_factors: list[str] = Field(default_factory=list)
    strengths_and_protective_factors: list[str] = Field(default_factory=list)
    course_and_duration: list[str] = Field(default_factory=list)
    functioning_impact: list[str] = Field(default_factory=list)
    user_explanation: list[str] = Field(default_factory=list)
    prior_helpful_or_harmful_support: list[str] = Field(default_factory=list)
    preferred_help: list[str] = Field(default_factory=list)
    open_hypotheses: list[str] = Field(default_factory=list)
    current_focus: str | None = None
    proposed_focus: str | None = None
    evidence: dict[str, list[str]] = Field(default_factory=dict)
    last_reviewed_at: str | None = None


class MemoryObservation(BaseModel):
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=500)
    evidence_quote: str | None = Field(default=None, max_length=500)
    aliases: list[str] = Field(default_factory=list, max_length=5)
    merge_into_id: str | None = None


class MemoryCorrection(BaseModel):
    memory_id: str
    replacement: str = Field(min_length=1, max_length=500)
    evidence_quote: str = Field(min_length=1, max_length=500)


class MemoryItem(BaseModel):
    id: str
    kind: MemoryKind
    content: str
    status: MemoryStatus
    evidence_message_ids: list[int] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list, max_length=5)
    superseded_content: list[str] = Field(default_factory=list)
    first_seen_at: str
    last_seen_at: str


class SessionRecord(BaseModel):
    id: str
    started_at: str
    last_activity_at: str
    ended_at: str | None = None
    summary: str = ""
    themes: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    user_response: str = ""
    open_questions: list[str] = Field(default_factory=list)
    consolidation_error: str | None = None


class InterventionRecord(BaseModel):
    id: str
    skill: str
    description: str = Field(min_length=1, max_length=500)
    prediction: str | None = Field(default=None, max_length=500)
    state: InterventionState
    linked_memory_ids: list[str] = Field(default_factory=list, max_length=5)
    evidence_message_ids: list[int] = Field(default_factory=list)
    outcome: str | None = Field(default=None, max_length=500)
    user_appraisal: str | None = Field(default=None, max_length=500)
    follow_up_at: str | None = None
    created_at: str
    updated_at: str


class ContextMemoryItem(BaseModel):
    id: str
    kind: MemoryKind
    content: str
    status: MemoryStatus
    last_seen_at: str


class WorkingContext(BaseModel):
    formulation: CaseFormulation
    confirmed_memory: list[ContextMemoryItem]
    hypotheses: list[ContextMemoryItem]
    recent_sessions: list[SessionRecord]
    active_interventions: list[InterventionRecord]
    relevant_excerpts: list[str]


FORMULATION_FIELDS = tuple(
    name
    for name, field in CaseFormulation.model_fields.items()
    if name not in {"current_focus", "proposed_focus", "evidence", "last_reviewed_at"}
    and field.annotation == list[str]
)


class MemoryError(RuntimeError):
    pass


class MemoryStore:
    def __init__(
        self,
        directory: Path | None = None,
        *,
        embedding_model: str | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        if (
            embedding_model
            and embedder is None
            and not embedding_model.startswith(("sentence-transformers:", "ollama:"))
        ):
            raise ValueError("Semantic memory requires a local embedding model.")
        if embedding_model and embedding_model.startswith("ollama:"):
            os.environ["OLLAMA_BASE_URL"] = LOCAL_OLLAMA_EMBEDDINGS_URL
        self.directory = directory or Path.home() / ".therapist"
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        self.database_path = self.directory / "thera.db"
        encryption_key = self._load_or_create_key()
        self._cipher = Fernet(encryption_key)
        self._hash_key = encryption_key
        self._transaction: sqlite3.Connection | None = None
        self._embedding_model = embedding_model or ("injected" if embedder else None)
        self._embedder = embedder or (Embedder(embedding_model) if embedding_model else None)
        with self._connect() as database:
            database.executescript(
                """
                CREATE TABLE IF NOT EXISTS state (
                    name TEXT PRIMARY KEY, payload BLOB NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, started_at TEXT NOT NULL,
                    last_activity_at TEXT NOT NULL, ended_at TEXT, payload BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                    role TEXT NOT NULL, created_at TEXT NOT NULL, payload BLOB NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
                    payload BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS interventions (
                    id TEXT PRIMARY KEY, state TEXT NOT NULL,
                    updated_at TEXT NOT NULL, payload BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_index (
                    entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    content_hash TEXT NOT NULL, dimensions INTEGER NOT NULL,
                    payload BLOB NOT NULL,
                    PRIMARY KEY(entity_type, entity_id)
                );
                """
            )
            semantic_columns = {
                row[1] for row in database.execute("PRAGMA table_info(semantic_index)")
            }
            if "entity_type" not in semantic_columns:
                database.execute("DROP TABLE semantic_index")
                database.execute(
                    "CREATE TABLE semantic_index ("
                    "entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, "
                    "model TEXT NOT NULL, content_hash TEXT NOT NULL, "
                    "dimensions INTEGER NOT NULL, payload BLOB NOT NULL, "
                    "PRIMARY KEY(entity_type, entity_id))"
                )
        self._migrate_legacy_state()

    def load_app_state(self) -> AppState:
        payload = self._read_state("app")
        return AppState() if payload is None else AppState.model_validate_json(payload)

    def save_app_state(self, state: AppState) -> None:
        self._write_state("app", state.model_dump_json().encode())

    def load_formulation(self) -> CaseFormulation:
        payload = self._read_state("formulation")
        if payload is None:
            return CaseFormulation()
        return CaseFormulation.model_validate_json(payload)

    def save_formulation(self, formulation: CaseFormulation, now: datetime | None = None) -> None:
        formulation.last_reviewed_at = _iso(now)
        self._write_state("formulation", formulation.model_dump_json().encode())

    def save_formulation_links(
        self,
        links: dict[str, list[str]],
        *,
        proposed_focus: str | None = None,
        current_focus: str | None = None,
        merge_existing: bool = False,
        remove_links: dict[str, list[str]] | None = None,
        now: datetime | None = None,
    ) -> CaseFormulation:
        active = {item.id: item for item in self.list_memory()}
        if merge_existing:
            existing_links = self.load_formulation().evidence
            remove_links = remove_links or {}
            links = {
                field_name: list(
                    dict.fromkeys(
                        [
                            *(
                                item_id
                                for item_id in existing_links.get(field_name, [])
                                if item_id not in remove_links.get(field_name, [])
                            ),
                            *links.get(field_name, []),
                        ]
                    )
                )[:5]
                for field_name in FORMULATION_FIELDS
            }
        formulation = CaseFormulation(
            current_focus=current_focus,
            proposed_focus=proposed_focus,
        )
        for field_name in FORMULATION_FIELDS:
            expected_statuses = (
                {MemoryStatus.AGENT_HYPOTHESIS}
                if field_name == "open_hypotheses"
                else {MemoryStatus.USER_CONFIRMED, MemoryStatus.USER_CORRECTED}
            )
            ids = [
                item_id
                for item_id in links.get(field_name, [])
                if item_id in active and active[item_id].status in expected_statuses
            ]
            if ids:
                setattr(formulation, field_name, [active[item_id].content for item_id in ids])
                formulation.evidence[field_name] = ids
        self.save_formulation(formulation, now)
        return formulation

    def start_session(self, now: datetime | None = None) -> SessionRecord:
        timestamp = _iso(now)
        session = SessionRecord(
            id=uuid4().hex[:12], started_at=timestamp, last_activity_at=timestamp
        )
        with self._connect() as database:
            database.execute(
                "INSERT INTO sessions(id, started_at, last_activity_at, payload) "
                "VALUES (?, ?, ?, ?)",
                (session.id, timestamp, timestamp, self._encrypt_model(session)),
            )
        return session

    def active_session(self) -> SessionRecord | None:
        with self._connect() as database:
            row = database.execute(
                "SELECT payload FROM sessions WHERE ended_at IS NULL "
                "ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
        return None if row is None else self._decrypt_model(row[0], SessionRecord)

    def session_expired(self, session: SessionRecord, now: datetime | None = None) -> bool:
        return (now or _now()) - datetime.fromisoformat(session.last_activity_at) >= SESSION_GAP

    def save_session(self, session: SessionRecord) -> None:
        with self._connect() as database:
            database.execute(
                "UPDATE sessions SET last_activity_at = ?, ended_at = ?, payload = ? WHERE id = ?",
                (
                    session.last_activity_at,
                    session.ended_at,
                    self._encrypt_model(session),
                    session.id,
                ),
            )

    def close_session(
        self,
        session: SessionRecord,
        *,
        summary: str = "",
        themes: list[str] | None = None,
        interventions: list[str] | None = None,
        user_response: str = "",
        open_questions: list[str] | None = None,
        consolidation_error: str | None = None,
        now: datetime | None = None,
    ) -> SessionRecord:
        session.ended_at = _iso(now)
        session.last_activity_at = session.ended_at
        session.summary = summary
        session.themes = themes or []
        session.interventions = interventions or []
        session.user_response = user_response
        session.open_questions = open_questions or []
        session.consolidation_error = consolidation_error
        self.save_session(session)
        return session

    def list_sessions(self, limit: int | None = None) -> list[SessionRecord]:
        sql = "SELECT payload FROM sessions ORDER BY started_at DESC"
        parameters: tuple[int, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            parameters = (limit,)
        with self._connect() as database:
            rows = database.execute(sql, parameters).fetchall()
        return [self._decrypt_model(row[0], SessionRecord) for row in rows]

    def save_turn(
        self,
        session: SessionRecord,
        user_text: str,
        assistant_text: str,
        model_messages: list[ModelMessage],
        now: datetime | None = None,
    ) -> int:
        timestamp = _iso(now)
        session.last_activity_at = timestamp
        user_payload = self._encrypt_json({"content": user_text})
        assistant_payload = self._encrypt_json(
            {
                "content": assistant_text,
                "model_messages": json.loads(ModelMessagesTypeAdapter.dump_json(model_messages)),
            }
        )
        with self._connect() as database:
            cursor = database.execute(
                "INSERT INTO messages(session_id, role, created_at, payload) "
                "VALUES (?, 'user', ?, ?)",
                (session.id, timestamp, user_payload),
            )
            user_message_id = int(cursor.lastrowid)
            database.execute(
                "INSERT INTO messages(session_id, role, created_at, payload) "
                "VALUES (?, 'assistant', ?, ?)",
                (session.id, timestamp, assistant_payload),
            )
            database.execute(
                "UPDATE sessions SET last_activity_at = ?, payload = ? WHERE id = ?",
                (timestamp, self._encrypt_model(session), session.id),
            )
        return user_message_id

    def load_session_history(self, session_id: str, limit: int = 20) -> list[ModelMessage]:
        with self._connect() as database:
            rows = database.execute(
                "SELECT payload FROM messages WHERE session_id = ? AND role = 'assistant' "
                "ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        groups: list[list[ModelMessage]] = []
        for row in reversed(rows):
            payload = self._decrypt_json(row[0])
            groups.append(
                ModelMessagesTypeAdapter.validate_python(payload.get("model_messages", []))
            )
        selected: list[list[ModelMessage]] = []
        used = 0
        for group in reversed(groups):
            if selected and used + len(group) > limit:
                break
            if len(group) > limit:
                continue
            selected.append(group)
            used += len(group)
        return [message for group in reversed(selected) for message in group]

    def session_transcript(self, session_id: str, limit_chars: int | None = None) -> str:
        with self._connect() as database:
            rows = database.execute(
                "SELECT role, payload FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        lines = [
            f"{role}: {self._decrypt_json(payload).get('content', '')}" for role, payload in rows
        ]
        if limit_chars is None:
            return "\n".join(lines)
        turns = ["\n".join(lines[index : index + 2]) for index in range(0, len(lines), 2)]
        selected: list[str] = []
        used = 0
        for turn in reversed(turns):
            if selected and used + len(turn) + 1 > limit_chars:
                break
            if len(turn) > limit_chars:
                continue
            selected.append(turn)
            used += len(turn) + 1
        return "\n".join(reversed(selected))

    def add_observations(
        self,
        observations: list[MemoryObservation],
        evidence_message_id: int,
        now: datetime | None = None,
        *,
        evidence_text: str | None = None,
    ) -> list[MemoryItem]:
        saved: list[MemoryItem] = []
        existing = self.list_memory(include_archived=True)
        for observation in observations:
            content = " ".join(observation.content.split()).strip()
            if not content:
                continue
            if (
                evidence_text is not None
                and observation.kind in {MemoryKind.FACT, MemoryKind.PREFERENCE, MemoryKind.EVENT}
                and not _supported_quote(observation.evidence_quote, evidence_text)
            ):
                continue
            duplicate = next(
                (
                    item
                    for item in existing
                    if item.id == observation.merge_into_id
                    and item.kind == observation.kind
                    and item.status is not MemoryStatus.ARCHIVED
                ),
                None,
            ) or next(
                (
                    item
                    for item in existing
                    if item.kind == observation.kind
                    and item.status is not MemoryStatus.ARCHIVED
                    and (
                        item.content.casefold() == content.casefold()
                        or _near_duplicate(item.content, content)
                    )
                ),
                None,
            )
            if duplicate:
                duplicate.last_seen_at = _iso(now)
                if evidence_message_id not in duplicate.evidence_message_ids:
                    duplicate.evidence_message_ids.append(evidence_message_id)
                duplicate.aliases = list(dict.fromkeys([*duplicate.aliases, *observation.aliases]))[
                    :5
                ]
                self._save_memory_item(duplicate)
                saved.append(duplicate)
                continue
            status = (
                MemoryStatus.AGENT_HYPOTHESIS
                if observation.kind in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS}
                else MemoryStatus.USER_CONFIRMED
            )
            timestamp = _iso(now)
            item = MemoryItem(
                id=uuid4().hex[:12],
                kind=observation.kind,
                content=content,
                status=status,
                evidence_message_ids=[evidence_message_id],
                aliases=observation.aliases,
                first_seen_at=timestamp,
                last_seen_at=timestamp,
            )
            self._save_memory_item(item)
            existing.append(item)
            saved.append(item)
        return saved

    def list_memory(self, include_archived: bool = False) -> list[MemoryItem]:
        sql = "SELECT payload FROM memory_items"
        parameters: tuple[str, ...] = ()
        if not include_archived:
            sql += " WHERE status != ?"
            parameters = (MemoryStatus.ARCHIVED.value,)
        sql += " ORDER BY last_seen_at DESC"
        with self._connect() as database:
            rows = database.execute(sql, parameters).fetchall()
        return [self._decrypt_model(row[0], MemoryItem) for row in rows]

    def confirm_memory(self, item_id: str, now: datetime | None = None) -> MemoryItem:
        with self.transaction():
            item = self._get_memory(item_id)
            item.status = MemoryStatus.USER_CONFIRMED
            item.last_seen_at = _iso(now)
            self._save_memory_item(item)
            self._delete_semantic_entities(
                "message", [str(value) for value in item.evidence_message_ids]
            )
            self._refresh_formulation_links()
            self._clear_pending_hypothesis(item.id)
            return item

    def correct_memory(
        self,
        item_id: str,
        content: str,
        evidence_message_id: int | None = None,
        now: datetime | None = None,
    ) -> MemoryItem:
        with self.transaction():
            content = " ".join(content.split()).strip()
            if not content:
                raise ValueError("Correction cannot be empty.")
            item = self._get_memory(item_id)
            old = item.content
            item.superseded_content.append(old)
            item.content = content
            item.status = MemoryStatus.USER_CORRECTED
            item.aliases = []
            if (
                evidence_message_id is not None
                and evidence_message_id not in item.evidence_message_ids
            ):
                item.evidence_message_ids.append(evidence_message_id)
            item.last_seen_at = _iso(now)
            self._save_memory_item(item)
            self._refresh_formulation_links()
            self._replace_derived_text(old, content)
            self._clear_pending_hypothesis(item.id)
            return item

    def forget_memory(self, item_id: str) -> MemoryItem:
        with self.transaction():
            item = self._get_memory(item_id)
            item.status = MemoryStatus.ARCHIVED
            item.last_seen_at = _iso()
            self._save_memory_item(item)
            self._delete_semantic_entities("memory", [item.id])
            self._delete_semantic_entities(
                "message", [str(value) for value in item.evidence_message_ids]
            )
            self._refresh_formulation_links()
            self._replace_derived_text(item.content, "", forgotten_id=item.id)
            self._clear_pending_hypothesis(item.id)
            return item

    def create_intervention(
        self,
        *,
        skill: str,
        description: str,
        prediction: str | None,
        state: InterventionState,
        linked_memory_ids: list[str],
        evidence_message_id: int,
        follow_up_at: str | None = None,
        now: datetime | None = None,
    ) -> InterventionRecord:
        if state not in {InterventionState.OFFERED, InterventionState.AGREED}:
            raise ValueError("A new intervention must be offered or agreed.")
        timestamp = _iso(now)
        active_memory_ids = {item.id for item in self.list_memory()}
        record = InterventionRecord(
            id=uuid4().hex[:12],
            skill=skill,
            description=" ".join(description.split()),
            prediction=" ".join(prediction.split()) if prediction else None,
            state=state,
            linked_memory_ids=[
                item_id for item_id in linked_memory_ids if item_id in active_memory_ids
            ][:5],
            evidence_message_ids=[evidence_message_id],
            follow_up_at=follow_up_at,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._save_intervention(record)
        return record

    def update_intervention(
        self,
        record_id: str,
        *,
        state: InterventionState,
        evidence_message_id: int,
        description: str | None = None,
        prediction: str | None = None,
        linked_memory_ids: list[str] | None = None,
        outcome: str | None = None,
        user_appraisal: str | None = None,
        follow_up_at: str | None = None,
        now: datetime | None = None,
    ) -> InterventionRecord:
        record = self._get_intervention(record_id)
        if not valid_intervention_transition(record.state, state):
            raise ValueError(f"Invalid intervention transition: {record.state} -> {state}")
        record.state = state
        record.description = " ".join(description.split()) if description else record.description
        record.prediction = " ".join(prediction.split()) if prediction else record.prediction
        if linked_memory_ids is not None:
            active_memory_ids = {item.id for item in self.list_memory()}
            record.linked_memory_ids = [
                item_id for item_id in linked_memory_ids if item_id in active_memory_ids
            ][:5]
        record.outcome = " ".join(outcome.split()) if outcome else record.outcome
        record.user_appraisal = (
            " ".join(user_appraisal.split()) if user_appraisal else record.user_appraisal
        )
        record.follow_up_at = follow_up_at or record.follow_up_at
        if evidence_message_id not in record.evidence_message_ids:
            record.evidence_message_ids.append(evidence_message_id)
        record.updated_at = _iso(now)
        self._save_intervention(record)
        return record

    def list_interventions(self, active_only: bool = False) -> list[InterventionRecord]:
        sql = "SELECT payload FROM interventions"
        parameters: tuple[str, ...] = ()
        if active_only:
            sql += " WHERE state IN (?, ?, ?, ?)"
            parameters = (
                InterventionState.OFFERED.value,
                InterventionState.AGREED.value,
                InterventionState.TRIED.value,
                InterventionState.NOT_TRIED.value,
            )
        sql += " ORDER BY updated_at DESC"
        with self._connect() as database:
            rows = database.execute(sql, parameters).fetchall()
        return [self._decrypt_model(row[0], InterventionRecord) for row in rows]

    def working_context(self, query: str) -> WorkingContext:
        memories = self.list_memory()
        semantic_scores = self._semantic_scores(query, memories)
        app_state = self.load_app_state()
        pending_ids = {app_state.pending_hypothesis_id}
        memories.sort(
            key=lambda item: (
                item.id in pending_ids,
                _hybrid_score(query, item, semantic_scores.get(item.id)),
                item.last_seen_at,
            ),
            reverse=True,
        )
        confirmed = [
            ContextMemoryItem.model_validate(item, from_attributes=True)
            for item in memories
            if item.status in {MemoryStatus.USER_CONFIRMED, MemoryStatus.USER_CORRECTED}
        ][:30]
        hypotheses = [
            ContextMemoryItem.model_validate(item, from_attributes=True)
            for item in memories
            if item.status is MemoryStatus.AGENT_HYPOTHESIS
        ][:10]
        recent_sessions = [session for session in self.list_sessions() if session.ended_at][:3]
        interventions = self.list_interventions(active_only=True)
        intervention_scores = self._semantic_text_scores(
            query,
            "intervention",
            {
                item.id: " ".join(
                    value
                    for value in (
                        item.description,
                        item.prediction,
                        item.outcome,
                        item.user_appraisal,
                    )
                    if value
                )
                for item in interventions
            },
        )
        interventions.sort(
            key=lambda item: (
                item.id == app_state.pending_intervention_id,
                _hybrid_text_score(
                    query,
                    " ".join(
                        value
                        for value in (
                            item.description,
                            item.prediction,
                            item.outcome,
                            item.user_appraisal,
                        )
                        if value
                    ),
                    intervention_scores.get(item.id),
                ),
                item.updated_at,
            ),
            reverse=True,
        )
        all_memory = self.list_memory(include_archived=True)
        excluded = {
            text.casefold()
            for item in all_memory
            for text in (
                ([item.content] if item.status is MemoryStatus.ARCHIVED else [])
                + item.superseded_content
            )
            if text
        }
        excluded_message_ids = {
            message_id
            for item in all_memory
            if item.status in {MemoryStatus.USER_CORRECTED, MemoryStatus.ARCHIVED}
            for message_id in item.evidence_message_ids
        }
        candidates = self._archive_candidates(excluded_message_ids)
        candidate_text = dict(candidates)
        excerpt_scores = self._semantic_text_scores(query, "message", candidate_text)
        excerpts = [
            text
            for _, _, message_id, text in sorted(
                (
                    (
                        _hybrid_text_score(query, text, excerpt_scores.get(message_id)),
                        -position,
                        message_id,
                        text,
                    )
                    for position, (message_id, text) in enumerate(candidates)
                ),
                reverse=True,
            )
            if (_lexical_score(query, text) > 0 or excerpt_scores.get(message_id, 0.0) >= 0.3)
            and not any(old in text.casefold() for old in excluded)
        ][:5]
        return WorkingContext(
            formulation=self.load_formulation(),
            confirmed_memory=confirmed,
            hypotheses=hypotheses,
            recent_sessions=recent_sessions,
            active_interventions=interventions[:5],
            relevant_excerpts=excerpts,
        )

    def export(self) -> dict[str, Any]:
        with self._connect() as database:
            rows = database.execute(
                "SELECT id, session_id, role, created_at, payload FROM messages ORDER BY id"
            ).fetchall()
        messages = [
            {
                "id": row[0],
                "session_id": row[1],
                "role": row[2],
                "created_at": row[3],
                "content": self._decrypt_json(row[4]).get("content", ""),
            }
            for row in rows
        ]
        return {
            "app": self.load_app_state().model_dump(),
            "case_formulation": self.load_formulation().model_dump(),
            "memory": [item.model_dump(mode="json") for item in self.list_memory(True)],
            "interventions": [item.model_dump(mode="json") for item in self.list_interventions()],
            "sessions": [session.model_dump() for session in self.list_sessions()],
            "messages": messages,
        }

    def load_secret(self, name: str) -> bytes | None:
        return self._read_state(f"secret:{name}")

    def save_secret(self, name: str, payload: bytes) -> None:
        self._write_state(f"secret:{name}", payload)

    def delete_secret(self, name: str) -> None:
        with self._connect() as database:
            database.execute("DELETE FROM state WHERE name = ?", (f"secret:{name}",))

    def delete_all(self) -> None:
        with self._connect() as database:
            database.execute("DELETE FROM semantic_index")
            database.execute("DELETE FROM messages")
            database.execute("DELETE FROM sessions")
            database.execute("DELETE FROM memory_items")
            database.execute("DELETE FROM interventions")
            database.execute("DELETE FROM state")

    def _save_memory_item(self, item: MemoryItem) -> None:
        with self._connect() as database:
            database.execute(
                "INSERT INTO memory_items(id, kind, status, first_seen_at, last_seen_at, payload) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                "kind = excluded.kind, status = excluded.status, "
                "last_seen_at = excluded.last_seen_at, payload = excluded.payload",
                (
                    item.id,
                    item.kind.value,
                    item.status.value,
                    item.first_seen_at,
                    item.last_seen_at,
                    self._encrypt_model(item),
                ),
            )

    def _save_intervention(self, item: InterventionRecord) -> None:
        with self._connect() as database:
            database.execute(
                "INSERT INTO interventions(id, state, updated_at, payload) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET state = excluded.state, "
                "updated_at = excluded.updated_at, payload = excluded.payload",
                (item.id, item.state.value, item.updated_at, self._encrypt_model(item)),
            )

    def _get_intervention(self, record_id: str) -> InterventionRecord:
        with self._connect() as database:
            row = database.execute(
                "SELECT payload FROM interventions WHERE id = ?", (record_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown intervention: {record_id}")
        return self._decrypt_model(row[0], InterventionRecord)

    def _get_memory(self, item_id: str) -> MemoryItem:
        with self._connect() as database:
            row = database.execute(
                "SELECT payload FROM memory_items WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown memory: {item_id}")
        return self._decrypt_model(row[0], MemoryItem)

    def _archive_candidates(self, excluded_message_ids: set[int]) -> list[tuple[str, str]]:
        with self._connect() as database:
            rows = database.execute(
                "SELECT id, payload FROM messages WHERE role = 'user' ORDER BY id DESC LIMIT 1000"
            ).fetchall()
        return [
            (str(message_id), self._decrypt_json(payload).get("content", ""))
            for message_id, payload in rows
            if message_id not in excluded_message_ids
        ]

    def _semantic_scores(self, query: str, memories: list[MemoryItem]) -> dict[str, float]:
        return self._semantic_text_scores(
            query,
            "memory",
            {item.id: " ".join([item.content, *item.aliases]) for item in memories},
        )

    def _semantic_text_scores(
        self, query: str, entity_type: str, texts: dict[str, str]
    ) -> dict[str, float]:
        if not self._embedder or not self._embedding_model or not query.strip() or not texts:
            return {}
        try:
            expected = {entity_id: self._content_hash(text) for entity_id, text in texts.items()}
            with self._connect() as database:
                rows = database.execute(
                    "SELECT entity_id, content_hash, dimensions, payload "
                    "FROM semantic_index WHERE model = ? AND entity_type = ?",
                    (self._embedding_model, entity_type),
                ).fetchall()
            vectors: dict[str, list[float]] = {}
            for entity_id, content_hash, dimensions, payload in rows:
                vector = self._decrypt_json(payload)["vector"]
                if expected.get(entity_id) == content_hash and len(vector) == dimensions:
                    vectors[entity_id] = vector
            missing = {
                entity_id: text for entity_id, text in texts.items() if entity_id not in vectors
            }
            if missing:
                result = self._embedder.embed_documents_sync(list(missing.values()))
                with self._connect() as database:
                    for entity_id, vector in zip(missing, result.embeddings, strict=True):
                        stored = list(vector)
                        vectors[entity_id] = stored
                        database.execute(
                            "INSERT INTO semantic_index(entity_type, entity_id, model, "
                            "content_hash, dimensions, payload) VALUES (?, ?, ?, ?, ?, ?) "
                            "ON CONFLICT(entity_type, entity_id) DO UPDATE SET "
                            "model = excluded.model, "
                            "content_hash = excluded.content_hash, "
                            "dimensions = excluded.dimensions, payload = excluded.payload",
                            (
                                entity_type,
                                entity_id,
                                self._embedding_model,
                                expected[entity_id],
                                len(stored),
                                self._encrypt_json({"vector": stored}),
                            ),
                        )
            query_vector = list(self._embedder.embed_query_sync(query).embeddings[0])
            return {
                item_id: similarity
                for item_id, vector in vectors.items()
                if (similarity := _cosine_similarity(query_vector, vector)) is not None
            }
        except Exception as error:
            raise MemoryError(
                "Semantic memory is unavailable. Run `thera setup` and try again."
            ) from error

    def _delete_semantic_entities(self, entity_type: str, entity_ids: list[str]) -> None:
        if not entity_ids:
            return
        with self._connect() as database:
            database.executemany(
                "DELETE FROM semantic_index WHERE entity_type = ? AND entity_id = ?",
                ((entity_type, entity_id) for entity_id in entity_ids),
            )

    def _content_hash(self, content: str) -> str:
        return hmac.new(self._hash_key, content.encode(), hashlib.sha256).hexdigest()

    def _replace_derived_text(self, old: str, new: str, *, forgotten_id: str | None = None) -> None:
        formulation = self.load_formulation()
        changed = False
        if not formulation.evidence:
            for field_name, value in formulation:
                if isinstance(value, list):
                    replaced = [_replace_derived(value_item, old, new) for value_item in value]
                    replaced = [value_item for value_item in replaced if value_item]
                    if replaced != value:
                        setattr(formulation, field_name, replaced)
                        changed = True
        for field_name in ("current_focus", "proposed_focus"):
            value = getattr(formulation, field_name)
            if value:
                replaced = _replace_derived(value, old, new)
                if replaced != value:
                    setattr(formulation, field_name, replaced or None)
                    changed = True
        if changed:
            self.save_formulation(formulation)
        stopped_interventions: set[str] = set()
        for intervention in self.list_interventions():
            before = intervention.model_dump()
            if forgotten_id:
                intervention.linked_memory_ids = [
                    item_id for item_id in intervention.linked_memory_ids if item_id != forgotten_id
                ]
            intervention.description = _replace_derived(intervention.description, old, new)
            for field_name in ("prediction", "outcome", "user_appraisal"):
                value = getattr(intervention, field_name)
                if value:
                    setattr(intervention, field_name, _replace_derived(value, old, new) or None)
            if not intervention.description:
                intervention.description = "Content removed by user request."
                intervention.state = InterventionState.STOPPED
                intervention.updated_at = _iso()
                self._save_intervention(intervention)
                stopped_interventions.add(intervention.id)
            elif intervention.model_dump() != before:
                self._save_intervention(intervention)
        if stopped_interventions:
            app_state = self.load_app_state()
            if app_state.pending_intervention_id in stopped_interventions:
                app_state.pending_intervention_id = None
                self.save_app_state(app_state)
        for session in self.list_sessions():
            before = session.model_dump()
            session.summary = _replace_derived(session.summary, old, new)
            session.themes = [
                text for value in session.themes if (text := _replace_derived(value, old, new))
            ]
            session.interventions = [
                text
                for value in session.interventions
                if (text := _replace_derived(value, old, new))
            ]
            session.user_response = _replace_derived(session.user_response, old, new)
            session.open_questions = [
                text
                for value in session.open_questions
                if (text := _replace_derived(value, old, new))
            ]
            if session.model_dump() != before:
                self.save_session(session)

    def _refresh_formulation_links(self) -> None:
        formulation = self.load_formulation()
        if not formulation.evidence:
            return
        self.save_formulation_links(
            formulation.evidence,
            proposed_focus=formulation.proposed_focus,
            current_focus=formulation.current_focus,
        )

    def _clear_pending_hypothesis(self, item_id: str) -> None:
        app_state = self.load_app_state()
        if app_state.pending_hypothesis_id == item_id:
            app_state.pending_hypothesis_id = None
            self.save_app_state(app_state)

    def _migrate_legacy_state(self) -> None:
        if self._read_state("schema_version") is not None:
            return
        profile_payload = self._read_state("profile")
        if profile_payload:
            legacy = json.loads(profile_payload)
            state = AppState(consent_version=legacy.get("consent_version"))
            self.save_app_state(state)
            observations = [
                MemoryObservation(kind=MemoryKind.EVENT, content=value)
                for value in legacy.get("goals", []) + legacy.get("exercises", [])
            ]
            observations += [
                MemoryObservation(kind=MemoryKind.PREFERENCE, content=f"{key}: {value}")
                for key, value in legacy.get("preferences", {}).items()
            ]
            if legacy.get("summary"):
                observations.append(
                    MemoryObservation(kind=MemoryKind.EVENT, content=legacy["summary"])
                )
            if observations:
                self.add_observations(observations, 0)
        history_payload = self._read_state("history")
        if history_payload:
            session = self.start_session()
            history = ModelMessagesTypeAdapter.validate_json(history_payload)
            self.save_turn(session, "Imported legacy conversation", "", history)
            self.close_session(session, summary="Imported legacy conversation")
        self._write_state("schema_version", b"2")

    def _load_or_create_key(self) -> bytes:
        path = self.directory / "memory.key"
        try:
            key = path.read_bytes()
        except FileNotFoundError:
            key = Fernet.generate_key()
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(key)
        os.chmod(path, 0o600)
        return key

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._transaction is not None:
            yield
            return
        database = self._open_connection()
        self._transaction = database
        try:
            with database:
                yield
        finally:
            self._transaction = None
            database.close()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._transaction is not None:
            yield self._transaction
            return
        database = self._open_connection()
        try:
            with database:
                yield database
        finally:
            database.close()

    def _open_connection(self) -> sqlite3.Connection:
        database = sqlite3.connect(self.database_path, autocommit=False)
        database.execute("PRAGMA foreign_keys = ON")
        return database

    def _read_state(self, name: str) -> bytes | None:
        with self._connect() as database:
            row = database.execute("SELECT payload FROM state WHERE name = ?", (name,)).fetchone()
        return None if row is None else self._decrypt(row[0])

    def _write_state(self, name: str, payload: bytes) -> None:
        with self._connect() as database:
            database.execute(
                "INSERT INTO state(name, payload) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET payload = excluded.payload, "
                "updated_at = CURRENT_TIMESTAMP",
                (name, self._cipher.encrypt(payload)),
            )

    def _decrypt(self, payload: bytes) -> bytes:
        try:
            return self._cipher.decrypt(payload)
        except InvalidToken as error:
            raise MemoryError("The local key cannot decrypt this memory database.") from error

    def _encrypt_json(self, value: Any) -> bytes:
        return self._cipher.encrypt(json.dumps(value, ensure_ascii=False).encode())

    def _decrypt_json(self, payload: bytes) -> dict[str, Any]:
        return json.loads(self._decrypt(payload))

    def _encrypt_model(self, value: BaseModel) -> bytes:
        return self._cipher.encrypt(value.model_dump_json().encode())

    def _decrypt_model(self, payload: bytes, model: type[BaseModel]) -> Any:
        return model.model_validate_json(self._decrypt(payload))


def _tokens(text: str) -> set[str]:
    normalized = text.casefold()
    tokens = {token for token in re.findall(r"\w+", normalized) if len(token) >= 4}
    if any(
        "\u3040" <= character <= "\u30ff"
        or "\u3400" <= character <= "\u9fff"
        or "\u0e00" <= character <= "\u0e7f"
        for character in normalized
    ):
        characters = "".join(
            character
            for character in normalized
            if unicodedata.category(character)[0] in {"L", "M", "N"}
        )
        tokens.update(characters[index : index + 2] for index in range(max(0, len(characters) - 1)))
    return tokens


def _lexical_score(query: str, text: str) -> int:
    return len(_tokens(query) & _tokens(text))


def _hybrid_score(query: str, item: MemoryItem, semantic_score: float | None) -> float:
    return _hybrid_text_score(query, " ".join([item.content, *item.aliases]), semantic_score)


def _hybrid_text_score(query: str, text: str, semantic_score: float | None) -> float:
    lexical = min(_lexical_score(query, text), 3) / 3
    if semantic_score is None:
        return lexical
    return (0.7 * max(0.0, semantic_score)) + (0.3 * lexical)


def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return None
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def _near_duplicate(left: str, right: str) -> bool:
    # ponytail: a linear fuzzy scan is enough for one local user; add an index only if measured.
    if set(re.findall(r"\d+", left)) != set(re.findall(r"\d+", right)):
        return False
    negation = re.compile(r"\b(non|not|never|cannot|can't|isn't|doesn't|didn't|no)\b")
    if bool(negation.search(left.casefold())) != bool(negation.search(right.casefold())):
        return False
    normalized_left = " ".join(re.findall(r"\w+", left.casefold()))
    normalized_right = " ".join(re.findall(r"\w+", right.casefold()))
    return SequenceMatcher(None, normalized_left, normalized_right).ratio() >= 0.9


def _supported_quote(quote: str | None, evidence: str) -> bool:
    if not quote:
        return False
    normalized_quote = " ".join(quote.split()).casefold()
    normalized_evidence = " ".join(evidence.split()).casefold()
    return bool(normalized_quote) and normalized_quote in normalized_evidence


def _replace(value: str, old: str, new: str) -> str:
    return re.sub(re.escape(old), new, value, flags=re.IGNORECASE).strip()


def _replace_derived(value: str, old: str, new: str) -> str:
    replaced = _replace(value, old, new)
    if replaced != value:
        return replaced
    # A generated summary may paraphrase its evidence. Without field-level provenance, retaining a
    # strongly overlapping paraphrase could resurrect corrected or forgotten memory. Invalidating
    # that derived field is conservative and preferable to presenting stale personal information.
    if _lexical_score(old, value) >= 2:
        return ""
    return value

"""Encrypted longitudinal memory backed by standard-library SQLite."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field
from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter

SESSION_GAP = timedelta(hours=8)


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


class AppState(BaseModel):
    consent_version: str | None = None
    telegram_consent_version: str | None = None
    telegram_update_offset: int | None = Field(default=None, ge=0)
    default_model: str | None = None
    default_locale: str | None = None
    telegram_allowed_user_id: int | None = Field(default=None, gt=0)


class CaseFormulation(BaseModel):
    presenting_concerns: list[str] = Field(default_factory=list)
    emotions_and_triggers: list[str] = Field(default_factory=list)
    thoughts_and_behaviors: list[str] = Field(default_factory=list)
    coping_strategies: list[str] = Field(default_factory=list)
    relationship_patterns: list[str] = Field(default_factory=list)
    maintaining_factors: list[str] = Field(default_factory=list)
    strengths_and_protective_factors: list[str] = Field(default_factory=list)
    open_hypotheses: list[str] = Field(default_factory=list)
    current_focus: str | None = None
    last_reviewed_at: str | None = None


class MemoryObservation(BaseModel):
    kind: MemoryKind
    content: str


class MemoryItem(BaseModel):
    id: str
    kind: MemoryKind
    content: str
    status: MemoryStatus
    evidence_message_ids: list[int] = Field(default_factory=list)
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
    relevant_excerpts: list[str]


class MemoryError(RuntimeError):
    pass


class MemoryStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path.home() / ".therapist"
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        self.database_path = self.directory / "thera.db"
        self._cipher = Fernet(self._load_or_create_key())
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
                """
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

    def save_formulation(
        self, formulation: CaseFormulation, now: datetime | None = None
    ) -> None:
        formulation.last_reviewed_at = _iso(now)
        self._write_state("formulation", formulation.model_dump_json().encode())

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
        now: datetime | None = None,
    ) -> SessionRecord:
        session.ended_at = _iso(now)
        session.last_activity_at = session.ended_at
        session.summary = summary
        session.themes = themes or []
        session.interventions = interventions or []
        session.user_response = user_response
        session.open_questions = open_questions or []
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
                "UPDATE sessions SET last_activity_at = ? WHERE id = ?",
                (timestamp, session.id),
            )
        session.last_activity_at = timestamp
        return user_message_id

    def load_session_history(self, session_id: str, limit: int = 20) -> list[ModelMessage]:
        with self._connect() as database:
            rows = database.execute(
                "SELECT payload FROM messages WHERE session_id = ? AND role = 'assistant' "
                "ORDER BY id DESC LIMIT ?",
                (session_id, limit // 2),
            ).fetchall()
        history: list[ModelMessage] = []
        for row in reversed(rows):
            payload = self._decrypt_json(row[0])
            history.extend(
                ModelMessagesTypeAdapter.validate_python(payload.get("model_messages", []))
            )
        return history[-limit:]

    def session_transcript(self, session_id: str) -> str:
        with self._connect() as database:
            rows = database.execute(
                "SELECT role, payload FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        return "\n".join(
            f"{role}: {self._decrypt_json(payload).get('content', '')}" for role, payload in rows
        )

    def add_observations(
        self,
        observations: list[MemoryObservation],
        evidence_message_id: int,
        now: datetime | None = None,
    ) -> list[MemoryItem]:
        saved: list[MemoryItem] = []
        existing = self.list_memory(include_archived=True)
        for observation in observations:
            content = " ".join(observation.content.split()).strip()
            if not content:
                continue
            duplicate = next(
                (
                    item
                    for item in existing
                    if item.kind == observation.kind
                    and item.content.casefold() == content.casefold()
                    and item.status is not MemoryStatus.ARCHIVED
                ),
                None,
            )
            if duplicate:
                duplicate.last_seen_at = _iso(now)
                if evidence_message_id not in duplicate.evidence_message_ids:
                    duplicate.evidence_message_ids.append(evidence_message_id)
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
        item = self._get_memory(item_id)
        item.status = MemoryStatus.USER_CONFIRMED
        item.last_seen_at = _iso(now)
        self._save_memory_item(item)
        return item

    def correct_memory(self, item_id: str, content: str) -> MemoryItem:
        content = " ".join(content.split()).strip()
        if not content:
            raise ValueError("Correction cannot be empty.")
        item = self._get_memory(item_id)
        old = item.content
        item.superseded_content.append(old)
        item.content = content
        item.status = MemoryStatus.USER_CORRECTED
        item.last_seen_at = _iso()
        self._save_memory_item(item)
        self._replace_derived_text(old, content)
        return item

    def forget_memory(self, item_id: str) -> MemoryItem:
        item = self._get_memory(item_id)
        item.status = MemoryStatus.ARCHIVED
        item.last_seen_at = _iso()
        self._save_memory_item(item)
        self._replace_derived_text(item.content, "")
        return item

    def working_context(self, query: str) -> WorkingContext:
        memories = self.list_memory()
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
        excerpts = [
            text
            for _, text in sorted(
                ((_lexical_score(query, text), text) for text in candidates), reverse=True
            )
            if _lexical_score(query, text) > 0
            and not any(old in text.casefold() for old in excluded)
        ][:5]
        return WorkingContext(
            formulation=self.load_formulation(),
            confirmed_memory=confirmed,
            hypotheses=hypotheses,
            recent_sessions=recent_sessions,
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
            database.execute("DELETE FROM messages")
            database.execute("DELETE FROM sessions")
            database.execute("DELETE FROM memory_items")
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

    def _get_memory(self, item_id: str) -> MemoryItem:
        with self._connect() as database:
            row = database.execute(
                "SELECT payload FROM memory_items WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown memory: {item_id}")
        return self._decrypt_model(row[0], MemoryItem)

    def _archive_candidates(self, excluded_message_ids: set[int]) -> list[str]:
        with self._connect() as database:
            rows = database.execute(
                "SELECT id, payload FROM messages WHERE role = 'user' ORDER BY id DESC LIMIT 1000"
            ).fetchall()
        return [
            self._decrypt_json(payload).get("content", "")
            for message_id, payload in rows
            if message_id not in excluded_message_ids
        ]

    def _replace_derived_text(self, old: str, new: str) -> None:
        formulation = self.load_formulation()
        changed = False
        for field_name, value in formulation:
            if isinstance(value, list):
                replaced = [_replace_derived(value_item, old, new) for value_item in value]
                replaced = [value_item for value_item in replaced if value_item]
                if replaced != value:
                    setattr(formulation, field_name, replaced)
                    changed = True
            elif isinstance(value, str):
                replaced = _replace_derived(value, old, new)
                if replaced != value:
                    setattr(formulation, field_name, replaced or None)
                    changed = True
        if changed:
            self.save_formulation(formulation)
        for session in self.list_sessions():
            before = session.model_dump()
            session.summary = _replace_derived(session.summary, old, new)
            session.themes = [
                text
                for value in session.themes
                if (text := _replace_derived(value, old, new))
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

    def _connect(self) -> sqlite3.Connection:
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
    return {token for token in re.findall(r"\w+", text.casefold()) if len(token) >= 4}


def _lexical_score(query: str, text: str) -> int:
    return len(_tokens(query) & _tokens(text))


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

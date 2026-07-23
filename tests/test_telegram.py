from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from therapist.memory import MemoryKind, MemoryObservation, MemoryStore
from therapist.telegram import TelegramBot, TelegramChannel, split_message


class FakeBot:
    def __init__(self, updates: list[list[dict[str, Any]]] | None = None) -> None:
        self.messages: list[tuple[int, str]] = []
        self.updates = iter(updates or [])
        self.deleted_webhook = False
        self.commands_set = False
        self.typing: list[int] = []
        self.interface: int | None = None

    def get_me(self) -> dict[str, str]:
        return {"username": "test_therapist_bot"}

    def delete_webhook(self) -> None:
        self.deleted_webhook = True

    def configure_interface(self, chat_id: int) -> None:
        self.commands_set = True
        self.interface = chat_id

    def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict[str, Any]]:
        try:
            return next(self.updates)
        except StopIteration as error:
            raise KeyboardInterrupt from error

    def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))

    def send_typing(self, chat_id: int) -> None:
        self.typing.append(chat_id)


class FakeSession:
    def __init__(self) -> None:
        self.received: list[str] = []
        self.end_calls = 0

    def respond(self, text: str) -> SimpleNamespace:
        self.received.append(text)
        return SimpleNamespace(text=f"reply: {text}")

    def end(self) -> None:
        self.end_calls += 1
        return None


def private_update(update_id: int, user_id: int, text: str) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id, "type": "private"},
            "text": text,
        },
    }


def test_channel_ignores_groups_and_users_outside_allowlist(tmp_path: Path) -> None:
    bot = FakeBot()
    session = FakeSession()
    channel = TelegramChannel(bot, session, MemoryStore(tmp_path), 42)  # type: ignore[arg-type]
    group = private_update(1, 42, "secret")
    group["message"]["chat"]["type"] = "group"

    assert channel.process_update(group) is False
    assert channel.process_update(private_update(2, 99, "secret")) is False
    assert bot.messages == []
    assert session.received == []


def test_channel_explains_unsupported_media_without_model(tmp_path: Path) -> None:
    bot = FakeBot()
    session = FakeSession()
    channel = TelegramChannel(bot, session, MemoryStore(tmp_path), 42)  # type: ignore[arg-type]
    update = private_update(1, 42, "placeholder")
    del update["message"]["text"]
    update["message"]["photo"] = [{"file_id": "opaque"}]

    assert channel.process_update(update) is True
    assert bot.messages == [
        (42, "I can only read and archive text. This content was not processed.")
    ]
    assert session.received == []


def test_channel_requires_separate_consent_then_uses_shared_session(
    tmp_path: Path,
) -> None:
    bot = FakeBot()
    session = FakeSession()
    store = MemoryStore(tmp_path)
    store_state = store.load_app_state()
    store_state.consent_version = "alpha-1"
    store.save_app_state(store_state)
    channel = TelegramChannel(bot, session, store, 42)  # type: ignore[arg-type]

    channel.process_update(private_update(1, 42, "Hello"))
    assert "/consent I UNDERSTAND" in bot.messages[-1][1]
    assert session.received == []

    channel.process_update(private_update(2, 42, "/consent I UNDERSTAND"))
    assert store.load_app_state().telegram_consent_version == "alpha-1"

    channel.process_update(private_update(3, 42, "/start"))
    assert "already recorded" in bot.messages[-1][1]

    channel.process_update(private_update(4, 42, "I feel stuck"))
    assert session.received == ["I feel stuck"]
    assert bot.messages[-1] == (42, "reply: I feel stuck")
    assert bot.typing == [42]


def test_run_persists_update_watermark_after_dispatch(tmp_path: Path) -> None:
    update = private_update(7, 42, "/start")
    bot = FakeBot([[update, update]])
    channel = TelegramChannel(
        bot,
        FakeSession(),
        MemoryStore(tmp_path),
        42,  # type: ignore[arg-type]
    )

    with pytest.raises(KeyboardInterrupt):
        channel.run()

    assert bot.deleted_webhook is True
    assert bot.commands_set is True
    assert bot.interface == 42
    assert len(bot.messages) == 1
    assert channel.store.load_app_state().telegram_update_offset == 8


def test_split_message_preserves_content_with_telegram_safe_chunks() -> None:
    text = ("word " * 1_100).strip()

    chunks = split_message(text)

    assert len(chunks) == 2
    assert all(len(chunk) <= 4_000 for chunk in chunks)
    assert " ".join(chunks) == text


def test_transparency_commands_show_status_memory_case_and_privacy(
    tmp_path: Path,
) -> None:
    bot = FakeBot()
    session = FakeSession()
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.telegram_consent_version = "alpha-1"
    state.embedding_model = "sentence-transformers:test"
    store.save_app_state(state)
    active = store.start_session()
    message_id = store.save_turn(active, "I avoid calls", "What happens?", [])
    item = store.add_observations(
        [
            MemoryObservation(
                kind=MemoryKind.FACT,
                content="The user avoids some difficult calls",
                evidence_quote="I avoid calls",
            )
        ],
        message_id,
        evidence_text="I avoid calls",
    )[0]
    formulation = store.load_formulation()
    formulation.presenting_concerns = [item.content]
    formulation.evidence = {"presenting_concerns": [item.id]}
    store.save_formulation(formulation)
    channel = TelegramChannel(bot, session, store, 42)  # type: ignore[arg-type]
    transcript_before = store.session_transcript(active.id)

    for update_id, command in enumerate(("/status", "/memory", "/case", "/privacy"), start=1):
        assert channel.process_update(private_update(update_id, 42, command)) is True

    output = "\n".join(message for _, message in bot.messages)
    assert "Active memory: 1 items" in output
    assert f"{item.id} · fact · confirmed" in output
    assert f"[evidence: {item.id}]" in output
    assert f"Evidence: messages {message_id}" in output
    assert "Telegram receives messages" in output
    assert "Internal prompts, tokens, and private reasoning are not shown" in output
    assert session.received == []
    assert store.session_transcript(active.id) == transcript_before
    assert "/status" not in store.session_transcript(active.id)


def test_memory_command_is_paginated(tmp_path: Path) -> None:
    bot = FakeBot()
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.telegram_consent_version = "alpha-1"
    store.save_app_state(state)
    session = store.start_session()
    for index in range(12):
        message_id = store.save_turn(session, f"fact {index}", "ok", [])
        store.add_observations(
            [
                MemoryObservation(
                    kind=MemoryKind.FACT,
                    content=f"Stable fact number {index}",
                    evidence_quote=f"fact {index}",
                )
            ],
            message_id,
            evidence_text=f"fact {index}",
        )
    channel = TelegramChannel(bot, FakeSession(), store, 42)  # type: ignore[arg-type]

    channel.process_update(private_update(1, 42, "/memory 2"))

    assert "page 2/2" in bot.messages[-1][1]
    assert bot.messages[-1][1].count(" · fact · confirmed") == 2


def test_normal_turn_discloses_committed_memory_change(tmp_path: Path) -> None:
    bot = FakeBot()
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.telegram_consent_version = "alpha-1"
    store.save_app_state(state)
    active = store.start_session()

    class RecordingSession(FakeSession):
        def respond(self, text: str) -> SimpleNamespace:
            message_id = store.save_turn(active, text, "Understood.", [])
            store.add_observations(
                [
                    MemoryObservation(
                        kind=MemoryKind.FACT,
                        content=text,
                        evidence_quote=text,
                    )
                ],
                message_id,
                evidence_text=text,
            )
            return SimpleNamespace(text="Understood.")

    channel = TelegramChannel(bot, RecordingSession(), store, 42)  # type: ignore[arg-type]

    channel.process_update(private_update(1, 42, "I work from home"))

    assert bot.messages[-1][1].startswith("Understood.\n\n")
    assert "THIS TURN'S RECORD" in bot.messages[-1][1]
    assert "Saved fact: I work from home" in bot.messages[-1][1]


def test_bot_configures_commands_only_for_allowlisted_chat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = TelegramBot("token")
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        bot,
        "_call",
        lambda method, payload: calls.append((method, payload)),
    )

    bot.configure_interface(42)

    assert calls[0] == ("deleteMyCommands", {})
    commands = calls[1][1]
    assert commands["scope"] == {"type": "chat", "chat_id": 42}
    assert {item["command"] for item in commands["commands"]} == {
        "start",
        "help",
        "status",
        "case",
        "memory",
        "sessions",
        "interventions",
        "privacy",
        "end",
    }
    assert calls[2][0] == "setMyDescription"

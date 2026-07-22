from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from therapist.memory import MemoryStore
from therapist.telegram import TelegramChannel, split_message


class FakeBot:
    def __init__(self, updates: list[list[dict[str, Any]]] | None = None) -> None:
        self.messages: list[tuple[int, str]] = []
        self.updates = iter(updates or [])
        self.deleted_webhook = False
        self.commands_set = False

    def get_me(self) -> dict[str, str]:
        return {"username": "test_therapist_bot"}

    def delete_webhook(self) -> None:
        self.deleted_webhook = True

    def set_commands(self) -> None:
        self.commands_set = True

    def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict[str, Any]]:
        try:
            return next(self.updates)
        except StopIteration as error:
            raise KeyboardInterrupt from error

    def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))


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
    channel = TelegramChannel(bot, session, MemoryStore(tmp_path), 42, "en-US")  # type: ignore[arg-type]
    group = private_update(1, 42, "secret")
    group["message"]["chat"]["type"] = "group"

    assert channel.process_update(group) is False
    assert channel.process_update(private_update(2, 99, "secret")) is False
    assert bot.messages == []
    assert session.received == []


def test_channel_consumes_media_without_model_or_reply(tmp_path: Path) -> None:
    bot = FakeBot()
    session = FakeSession()
    channel = TelegramChannel(bot, session, MemoryStore(tmp_path), 42, "en-US")  # type: ignore[arg-type]
    update = private_update(1, 42, "placeholder")
    del update["message"]["text"]
    update["message"]["photo"] = [{"file_id": "opaque"}]

    assert channel.process_update(update) is True
    assert bot.messages == []
    assert session.received == []


def test_channel_requires_separate_consent_then_uses_shared_session(tmp_path: Path) -> None:
    bot = FakeBot()
    session = FakeSession()
    store = MemoryStore(tmp_path)
    store_state = store.load_app_state()
    store_state.consent_version = "alpha-1"
    store.save_app_state(store_state)
    channel = TelegramChannel(bot, session, store, 42, "it-IT")  # type: ignore[arg-type]

    channel.process_update(private_update(1, 42, "Ciao"))
    assert "/consent CAPISCO" in bot.messages[-1][1]
    assert session.received == []

    channel.process_update(private_update(2, 42, "/consent CAPISCO"))
    assert store.load_app_state().telegram_consent_version == "alpha-1"

    channel.process_update(private_update(3, 42, "/start"))
    assert "già registrato" in bot.messages[-1][1]

    channel.process_update(private_update(4, 42, "Mi sento bloccato"))
    assert session.received == ["Mi sento bloccato"]
    assert bot.messages[-1] == (42, "reply: Mi sento bloccato")


def test_run_persists_update_watermark_after_dispatch(tmp_path: Path) -> None:
    update = private_update(7, 42, "/start")
    bot = FakeBot([[update, update]])
    channel = TelegramChannel(
        bot, FakeSession(), MemoryStore(tmp_path), 42, "en-US"  # type: ignore[arg-type]
    )

    with pytest.raises(KeyboardInterrupt):
        channel.run()

    assert bot.deleted_webhook is True
    assert bot.commands_set is True
    assert len(bot.messages) == 1
    assert channel.store.load_app_state().telegram_update_offset == 8


def test_split_message_preserves_content_with_telegram_safe_chunks() -> None:
    text = ("word " * 1_100).strip()

    chunks = split_message(text)

    assert len(chunks) == 2
    assert all(len(chunk) <= 4_000 for chunk in chunks)
    assert " ".join(chunks) == text

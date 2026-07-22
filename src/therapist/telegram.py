"""Private, single-user Telegram interface using the standard Bot API."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from therapist.chat import ChatSession
from therapist.memory import MemoryStore

API_ROOT = "https://api.telegram.org"
CONSENT_VERSION = "alpha-1"
MESSAGE_LIMIT = 4_000


class TelegramError(RuntimeError):
    """A privacy-safe Telegram transport error."""

    def __init__(self, message: str, *, fatal: bool = False) -> None:
        super().__init__(message)
        self.fatal = fatal


class TelegramBot:
    def __init__(self, token: str) -> None:
        token = token.strip()
        if not token:
            raise ValueError("Telegram bot token cannot be empty.")
        self._base_url = f"{API_ROOT}/bot{token}"

    def get_me(self) -> dict[str, Any]:
        result = self._call("getMe", {})
        if not isinstance(result, dict):
            raise TelegramError("Telegram returned an invalid bot identity.")
        return result

    def delete_webhook(self) -> None:
        self._call("deleteWebhook", {"drop_pending_updates": False})

    def set_commands(self) -> None:
        self._call(
            "setMyCommands",
            {
                "commands": [
                    {"command": "start", "description": "Privacy notice and consent"},
                    {"command": "help", "description": "Available commands"},
                    {"command": "end", "description": "Close the current session"},
                ]
            },
        )

    def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset
        result = self._call("getUpdates", payload, timeout=timeout + 10)
        if not isinstance(result, list):
            raise TelegramError("Telegram returned an invalid update list.")
        return [item for item in result if isinstance(item, dict)]

    def send_message(self, chat_id: int, text: str) -> None:
        for chunk in split_message(text):
            self._call("sendMessage", {"chat_id": chat_id, "text": chunk})

    def _call(self, method: str, payload: dict[str, Any], timeout: int = 20) -> Any:
        request = Request(
            f"{self._base_url}/{method}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "therapist-cli/0.1",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                body = json.load(response)
        except HTTPError as error:
            description = _http_error_description(error)
            raise TelegramError(
                f"Telegram API rejected the request: {description}",
                fatal=error.code in {400, 401, 409},
            ) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise TelegramError(
                "Telegram is unavailable or returned an invalid response."
            ) from error
        if not isinstance(body, dict) or body.get("ok") is not True:
            description = (
                body.get("description", "unknown error")
                if isinstance(body, dict)
                else "unknown error"
            )
            error_code = body.get("error_code") if isinstance(body, dict) else None
            raise TelegramError(
                f"Telegram API error: {description}", fatal=error_code in {400, 401, 409}
            )
        return body.get("result")


@dataclass
class TelegramChannel:
    bot: TelegramBot
    session: ChatSession
    store: MemoryStore
    allowed_user_id: int
    locale: str

    def run(self) -> None:
        identity = self.bot.get_me()
        self.bot.delete_webhook()
        self.bot.set_commands()
        username = identity.get("username", "unknown")
        print(f"Telegram bot @{username} is listening. Press Ctrl-C to stop.")
        offset = self.store.load_app_state().telegram_update_offset
        while True:
            try:
                updates = self.bot.get_updates(offset)
            except TelegramError as error:
                if error.fatal:
                    raise
                print(f"Telegram polling error: {error}")
                time.sleep(3)
                continue
            for update in updates:
                update_id = update.get("update_id")
                if not isinstance(update_id, int):
                    continue
                if offset is not None and update_id < offset:
                    continue
                try:
                    self.process_update(update)
                except TelegramError as error:
                    print(f"Telegram delivery error: {error}")
                finally:
                    offset = update_id + 1
                    state = self.store.load_app_state()
                    state.telegram_update_offset = offset
                    self.store.save_app_state(state)

    def process_update(self, update: dict[str, Any]) -> bool:
        message = update.get("message")
        if not isinstance(message, dict):
            return False
        chat = message.get("chat")
        sender = message.get("from")
        if not isinstance(chat, dict) or not isinstance(sender, dict):
            return False
        chat_id = chat.get("id")
        if (
            chat.get("type") != "private"
            or sender.get("id") != self.allowed_user_id
            or sender.get("is_bot") is True
            or not isinstance(chat_id, int)
        ):
            return False
        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            return True
        text = text.strip()
        if len(text) > MESSAGE_LIMIT:
            self.bot.send_message(chat_id, self._message_too_long())
            return True
        command = _command_name(text)
        state = self.store.load_app_state()
        if command == "/start":
            self.bot.send_message(
                chat_id,
                self._consent_notice(state.telegram_consent_version == CONSENT_VERSION),
            )
            return True

        consent = "I UNDERSTAND" if self.locale == "en-US" else "CAPISCO"
        if state.telegram_consent_version != CONSENT_VERSION:
            if text == f"/consent {consent}":
                state.telegram_consent_version = CONSENT_VERSION
                self.store.save_app_state(state)
                self.bot.send_message(chat_id, self._consent_recorded())
            else:
                self.bot.send_message(chat_id, self._consent_notice(False))
            return True

        if command:
            response = self._command_response(command)
            self.bot.send_message(chat_id, response or self._unknown_command())
            return True
        try:
            reply = self.session.respond(text).text
        except Exception as error:  # Provider SDKs expose different error types.
            print(f"Model error while handling Telegram message: {type(error).__name__}")
            reply = self._model_error()
        self.bot.send_message(chat_id, reply)
        return True

    def _command_response(self, command: str) -> str | None:
        if command == "/help":
            if self.locale == "it-IT":
                return (
                    "/start — informativa privacy\n/help — comandi disponibili\n"
                    "/end — chiudi la sessione attuale\n\n"
                    "Memoria, export, cancellazione e autenticazione restano nella CLI host."
                )
            return (
                "/start — privacy notice\n/help — available commands\n"
                "/end — close the current session\n\n"
                "Memory controls, export, deletion, and authentication stay on the host CLI."
            )
        if command == "/end":
            closed = self.session.end()
            if self.locale == "it-IT":
                return (
                    "Nessuna sessione attiva."
                    if closed is None
                    else "Sessione chiusa; trascrizione conservata."
                )
            return (
                "No active session."
                if closed is None
                else "Session closed; transcript preserved."
            )
        return None

    def _consent_notice(self, consented: bool) -> str:
        if self.locale == "it-IT":
            notice = (
                "Sono un'AI sperimentale, non un terapeuta o un servizio di emergenza. "
                "Telegram e l'eventuale provider remoto ricevono i tuoi messaggi. "
            )
            return notice + (
                "Il consenso è già registrato: puoi scrivermi."
                if consented
                else "Per continuare scrivi esattamente: /consent CAPISCO"
            )
        notice = (
            "I am an experimental AI, not a therapist or emergency service. "
            "Telegram and any configured remote provider receive your messages. "
        )
        return notice + (
            "Consent is already recorded: you can message me."
            if consented
            else "To continue, type exactly: /consent I UNDERSTAND"
        )

    def _consent_recorded(self) -> str:
        if self.locale == "it-IT":
            return "Consenso registrato. Puoi scrivermi o usare /help."
        return "Consent recorded. You can message me or use /help."

    def _message_too_long(self) -> str:
        if self.locale == "it-IT":
            return "Il messaggio è troppo lungo. Dividilo in parti più brevi."
        return "That message is too long. Please split it into shorter parts."

    def _unknown_command(self) -> str:
        return (
            "Comando sconosciuto. Usa /help."
            if self.locale == "it-IT"
            else "Unknown command. Use /help."
        )

    def _model_error(self) -> str:
        if self.locale == "it-IT":
            return "Non sono riuscito a rispondere. Riprova tra poco."
        return "I couldn't respond. Please try again shortly."


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    remaining = text.strip()
    if not remaining:
        return [" "]
    chunks: list[str] = []
    while len(remaining) > limit:
        boundary = max(
            remaining.rfind("\n\n", 0, limit + 1),
            remaining.rfind("\n", 0, limit + 1),
            remaining.rfind(" ", 0, limit + 1),
        )
        if boundary < limit // 2:
            boundary = limit
        chunks.append(remaining[:boundary].rstrip())
        remaining = remaining[boundary:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _command_name(text: str) -> str | None:
    first = text.split(maxsplit=1)[0]
    if not first.startswith("/"):
        return None
    return first.split("@", 1)[0].lower()


def _http_error_description(error: HTTPError) -> str:
    try:
        body = json.loads(error.read())
    except (OSError, json.JSONDecodeError):
        return f"HTTP {error.code}"
    if isinstance(body, dict) and isinstance(body.get("description"), str):
        return body["description"]
    return f"HTTP {error.code}"

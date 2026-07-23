"""Private, single-user Telegram interface using the standard Bot API."""

from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from therapist.chat import ChatSession, TurnStreamEvent, TurnStreamKind
from therapist.memory import MemoryStore

API_ROOT = "https://api.telegram.org"
CONSENT_VERSION = "alpha-1"
MESSAGE_LIMIT = 4_000
MEMORY_PAGE_SIZE = 10
SESSION_PAGE_SIZE = 5
INTERVENTION_PAGE_SIZE = 10
DRAFT_INTERVAL_SECONDS = 0.25


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

    def configure_interface(self, chat_id: int) -> None:
        commands = [
            ("start", "Notice and consent"),
            ("help", "Complete guide"),
            ("status", "Agent and archive status"),
            ("case", "Shared formulation"),
            ("memory", "Structured memory"),
            ("sessions", "Sessions and summaries"),
            ("interventions", "Recorded interventions"),
            ("privacy", "Data, providers and limits"),
            ("end", "Close the session"),
        ]
        self._call("deleteMyCommands", {})
        self._call(
            "setMyCommands",
            {
                "commands": [
                    {"command": command, "description": description}
                    for command, description in commands
                ],
                "scope": {"type": "chat", "chat_id": chat_id},
            },
        )
        self._call(
            "setMyDescription",
            {
                "description": "Private experimental AI with encrypted local memory. "
                "Not therapy, diagnosis, human monitoring, or an emergency service."
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

    def send_message_draft(self, chat_id: int, draft_id: int, text: str) -> None:
        self._call(
            "sendMessageDraft",
            {"chat_id": chat_id, "draft_id": draft_id, "text": text},
        )

    def send_rich_message_draft(self, chat_id: int, draft_id: int, text: str) -> None:
        self._call(
            "sendRichMessageDraft",
            {
                "chat_id": chat_id,
                "draft_id": draft_id,
                "rich_message": {"markdown": text},
            },
        )

    def send_rich_message(self, chat_id: int, text: str) -> None:
        self._call(
            "sendRichMessage",
            {"chat_id": chat_id, "rich_message": {"markdown": text}},
        )

    def send_typing(self, chat_id: int) -> None:
        self._call("sendChatAction", {"chat_id": chat_id, "action": "typing"})

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

    def run(self) -> None:
        identity = self.bot.get_me()
        self.bot.delete_webhook()
        self.bot.configure_interface(self.allowed_user_id)
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
            self.bot.send_message(chat_id, self._unsupported_message())
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

        consent = "I UNDERSTAND"
        if state.telegram_consent_version != CONSENT_VERSION:
            if text == f"/consent {consent}":
                state.telegram_consent_version = CONSENT_VERSION
                self.store.save_app_state(state)
                self.bot.send_message(chat_id, self._consent_recorded())
            else:
                self.bot.send_message(chat_id, self._consent_notice(False))
            return True

        if command:
            response = self._command_response(command, _command_argument(text))
            self.bot.send_message(chat_id, response or self._unknown_command())
            return True
        before = self._durable_snapshot()
        try:
            self.bot.send_typing(chat_id)
        except TelegramError as error:
            print(f"Telegram typing indicator error: {error}")
        draft_id = secrets.randbits(31) or 1
        last_draft_at = 0.0
        tool_delivery_failed = False

        def render(event: TurnStreamEvent) -> None:
            nonlocal last_draft_at, tool_delivery_failed
            if event.kind is not TurnStreamKind.REPLY:
                try:
                    self.bot.send_message(chat_id, event.text)
                except TelegramError as error:
                    tool_delivery_failed = True
                    print(f"Telegram tool trace delivery error: {error}")
                return
            now = time.monotonic()
            if now - last_draft_at < DRAFT_INTERVAL_SECONDS:
                return
            rich = _safe_rich_markdown(event.text)
            try:
                if rich:
                    self.bot.send_rich_message_draft(chat_id, draft_id, event.text)
                else:
                    self.bot.send_message_draft(chat_id, draft_id, event.text)
            except TelegramError as error:
                print(f"Telegram draft delivery error: {error}")
                if rich and error.fatal:
                    try:
                        self.bot.send_message_draft(chat_id, draft_id, event.text)
                    except TelegramError as fallback_error:
                        print(f"Telegram plain draft delivery error: {fallback_error}")
                    else:
                        last_draft_at = now
            else:
                last_draft_at = now

        try:
            turn = self.session.respond(text, on_event=render)
        except Exception as error:  # Provider SDKs expose different error types.
            print(f"Model error while handling Telegram message: {type(error).__name__}")
            reply = self._model_error()
            notice = None
            tool_trace = None
        else:
            reply = turn.text
            notice = getattr(turn, "notice", None)
            tool_trace = getattr(turn, "tool_trace", None)
        changes = self._durable_changes(before)
        if notice:
            self.bot.send_message(chat_id, notice)
        if tool_trace and tool_delivery_failed:
            self.bot.send_message(chat_id, tool_trace)
        if _safe_rich_markdown(reply):
            try:
                self.bot.send_rich_message(chat_id, reply)
            except TelegramError as error:
                print(f"Telegram rich message delivery error: {error}")
                self.bot.send_message(chat_id, reply)
        else:
            self.bot.send_message(chat_id, reply)
        if changes:
            self.bot.send_message(chat_id, changes)
        return True

    def _command_response(self, command: str, argument: str | None) -> str | None:
        if command == "/help":
            return (
                "CONVERSATION\n"
                "/start — identity, notice, and consent\n"
                "/status — agent, session, and archive status\n"
                "/end — close and summarize the session\n\n"
                "TRANSPARENCY\n"
                "/case — formulation and linked evidence\n"
                "/memory [page] — active facts and hypotheses\n"
                "/sessions [page|ID] — session summaries\n"
                "/interventions [page] — interventions and outcomes\n"
                "/privacy — data flow and limits\n\n"
                "Correction, forgetting, export, deletion, and authentication "
                "remain on the local CLI for safety."
            )
        if command == "/status":
            return self._status()
        if command == "/case":
            return self._case()
        if command == "/memory":
            return self._memory(argument)
        if command == "/sessions":
            return self._sessions(argument)
        if command == "/interventions":
            return self._interventions(argument)
        if command == "/privacy":
            return self._privacy()
        if command == "/end":
            closed = self.session.end()
            return (
                "No active session." if closed is None else "Session closed; transcript preserved."
            )
        return None

    def _status(self) -> str:
        state = self.store.load_app_state()
        session = self.store.active_session()
        memories = self.store.list_memory()
        sessions = self.store.list_sessions()
        completed_sessions = sum(item.ended_at is not None for item in sessions)
        interventions = self.store.list_interventions()
        formulation = self.store.load_formulation()
        session_status = (
            f"active since {_date(session.started_at)} · ID {session.id}"
            if session
            else "no active session"
        )
        context_status = (
            f"{session.last_context_tokens}/{self.session.context_window_tokens} estimated tokens"
            if session and hasattr(self.session, "context_window_tokens")
            else "not available"
        )
        return (
            "STATUS\n"
            "Identity: experimental AI, without human monitoring\n"
            "Channel: private Telegram chat with the authorized user\n"
            f"Model: {state.default_model or 'not configured'}\n"
            f"Session: {session_status}\n"
            f"Context: {context_status}\n"
            f"Active memory: {len(memories)} items\n"
            f"Sessions: {len(sessions)} ({completed_sessions} closed)\n"
            f"Recorded interventions: {len(interventions)}\n"
            f"Current focus: {formulation.current_focus or 'not set'}\n"
            "Semantic memory: "
            f"{'local and encrypted' if state.embedding_model else 'not configured'}"
        )

    def _case(self) -> str:
        formulation = self.store.load_formulation()
        labels = {
            "presenting_concerns": "Concerns",
            "emotions_and_triggers": "Emotions and triggers",
            "thoughts_and_behaviors": "Thoughts and behaviors",
            "coping_strategies": "Coping",
            "relationship_patterns": "Relationships",
            "maintaining_factors": "Maintaining factors",
            "strengths_and_protective_factors": "Strengths",
            "course_and_duration": "Course",
            "functioning_impact": "Impact",
            "user_explanation": "User explanation",
            "prior_helpful_or_harmful_support": "Helpful or harmful support",
            "preferred_help": "Preferences",
            "open_hypotheses": "Open hypotheses",
        }
        lines = ["SHARED FORMULATION"]
        if formulation.current_focus:
            lines.append(f"Focus: {formulation.current_focus}")
        if formulation.proposed_focus:
            lines.append(f"Proposed focus: {formulation.proposed_focus}")
        for field, label in labels.items():
            values = getattr(formulation, field)
            if not values:
                continue
            lines.append(f"\n{label}")
            evidence = formulation.evidence.get(field, [])
            lines.extend(
                f"• {value}"
                + (f" [evidence: {evidence[index]}]" if index < len(evidence) else "")
                for index, value in enumerate(values)
            )
        if len(lines) == 1:
            lines.append("It has not been built yet.")
        lines.append("\nInterpretations remain hypotheses until you confirm them.")
        return "\n".join(lines)

    def _memory(self, argument: str | None) -> str:
        items = self.store.list_memory()
        page, selected, pages = _page(items, argument, MEMORY_PAGE_SIZE)
        title = f"ACTIVE MEMORY · page {page}/{pages}"
        if not selected:
            return title + "\nNo active items."
        lines = [title]
        for item in selected:
            evidence = ", ".join(str(value) for value in item.evidence_message_ids)
            lines.append(
                f"\n{item.id} · {_memory_label(item.kind.value)} · "
                f"{_status_label(item.status.value)}\n{item.content}\n"
                + f"Evidence: messages {evidence} · updated {_date(item.last_seen_at)}"
            )
        lines.append("\nForgotten items are excluded. Use /memory N to change page.")
        return "\n".join(lines)

    def _sessions(self, argument: str | None) -> str:
        sessions = self.store.list_sessions()
        if argument:
            found = next((item for item in sessions if item.id == argument), None)
            if found is not None or not argument.isdecimal():
                return self._session_detail(found)
        page, selected, pages = _page(sessions, argument, SESSION_PAGE_SIZE)
        title = f"SESSIONS · page {page}/{pages}"
        if not selected:
            return title + "\nNo sessions."
        lines = [title]
        for item in selected:
            state = "active" if item.ended_at is None else "closed"
            summary = item.summary or "summary not available yet"
            lines.append(f"\n{item.id} · {_date(item.started_at)} · {state}\n{summary}")
        lines.append("\nUse /sessions N for a page or /sessions ID for details.")
        return "\n".join(lines)

    def _session_detail(self, session: Any) -> str:
        if session is None:
            return "Session not found."
        labels = ("Summary", "Themes", "Interventions", "Response", "Open questions")
        lines = [
            f"SESSION {session.id}",
            f"{_date(session.started_at)} → "
            + (_date(session.ended_at) if session.ended_at else "active"),
        ]
        values = (
            session.summary,
            session.themes,
            session.interventions,
            session.user_response,
            session.open_questions,
        )
        for label, value in zip(labels, values, strict=True):
            if value:
                content = (
                    "\n".join(f"• {item}" for item in value) if isinstance(value, list) else value
                )
                lines.append(f"\n{label}\n{content}")
        if session.consolidation_error:
            lines.append(f"\nConsolidation failed: {session.consolidation_error}")
        if session.end_reason:
            lines.append(f"\nClosed because: {session.end_reason.value}")
        return "\n".join(lines)

    def _interventions(self, argument: str | None) -> str:
        items = self.store.list_interventions()
        page, selected, pages = _page(items, argument, INTERVENTION_PAGE_SIZE)
        title = f"INTERVENTIONS · page {page}/{pages}"
        if not selected:
            return title + "\nNo recorded interventions."
        lines = [title]
        for item in selected:
            details = [
                f"\n{item.id} · {_status_label(item.state.value)}",
                f"Method: {item.skill}",
                item.description,
            ]
            if item.prediction:
                details.append(f"Prediction: {item.prediction}")
            if item.outcome:
                details.append(f"Outcome: {item.outcome}")
            if item.user_appraisal:
                details.append(f"Appraisal: {item.user_appraisal}")
            if item.linked_memory_ids:
                details.append("Linked memory: " + ", ".join(item.linked_memory_ids))
            if item.follow_up_at:
                details.append(f"Follow-up: {item.follow_up_at}")
            lines.extend(details)
        lines.append("\nUse /interventions N to change page.")
        return "\n".join(lines)

    def _privacy(self) -> str:
        return (
            "PRIVACY AND TRANSPARENCY\n"
            "• Telegram receives messages, replies, and data you ask to view here.\n"
            "• The model provider receives the message and only selected context.\n"
            "• Archive, structured memory, and semantic index stay encrypted on the host.\n"
            "• Semantic retrieval uses a local model; it does not establish facts or evidence.\n"
            "• No person reads or monitors the chat.\n"
            "• The bot cannot contact help, locate you, or act outside the chat.\n"
            "• Agent tool inputs and outputs are shown and retained in encrypted history.\n"
            "• Any durable changes are disclosed after each reply.\n"
            "• Internal prompts, tokens, and private reasoning are not shown.\n\n"
            "Use the local CLI for export, correction, forgetting, and full deletion."
        )

    def _durable_snapshot(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        return (
            {item.id: item for item in self.store.list_memory()},
            {item.id: item for item in self.store.list_interventions()},
            self.store.load_formulation().model_dump(),
        )

    def _durable_changes(
        self, before: tuple[dict[str, Any], dict[str, Any], dict[str, Any]]
    ) -> str | None:
        old_memory, old_interventions, old_formulation = before
        changes: list[str] = []
        for item in self.store.list_memory():
            old = old_memory.get(item.id)
            if old is None:
                label = _memory_label(item.kind.value)
                changes.append(f"Saved {label}: {item.content} [{item.id}]")
            elif old.content != item.content or old.status != item.status:
                changes.append(f"Memory updated: {item.content} [{item.id}]")
        for item in self.store.list_interventions():
            old = old_interventions.get(item.id)
            if old is None or old.model_dump() != item.model_dump():
                status = _status_label(item.state.value)
                changes.append(f"Intervention {status}: {item.description} [{item.id}]")
        formulation = self.store.load_formulation().model_dump()
        for field in ("current_focus", "proposed_focus"):
            if old_formulation.get(field) != formulation.get(field) and formulation.get(field):
                label = "Accepted focus" if field == "current_focus" else "Proposed focus"
                changes.append(f"{label}: {formulation[field]}")
        if not changes:
            return None
        return "THIS TURN'S RECORD\n" + "\n".join(f"• {change}" for change in changes)

    def _consent_notice(self, consented: bool) -> str:
        notice = (
            "I am an experimental AI, not a therapist or emergency service. "
            "Telegram receives messages, replies, and data you choose to view here; "
            "any remote provider receives messages and selected context. "
        )
        return notice + (
            "Consent is already recorded: you can message me."
            if consented
            else "To continue, type exactly: /consent I UNDERSTAND"
        )

    def _consent_recorded(self) -> str:
        return "Consent recorded. You can message me or use /help."

    def _message_too_long(self) -> str:
        return "That message is too long. Please split it into shorter parts."

    def _unsupported_message(self) -> str:
        return "I can only read and archive text. This content was not processed."

    def _unknown_command(self) -> str:
        return "Unknown command. Use /help."

    def _model_error(self) -> str:
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


def _safe_rich_markdown(text: str) -> bool:
    return "![" not in text and re.search(r"<[A-Za-z][^>]*>", text) is None


def _command_name(text: str) -> str | None:
    first = text.split(maxsplit=1)[0]
    if not first.startswith("/"):
        return None
    return first.split("@", 1)[0].lower()


def _command_argument(text: str) -> str | None:
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 and parts[1].strip() else None


def _page(items: list[Any], argument: str | None, size: int) -> tuple[int, list[Any], int]:
    pages = max(1, (len(items) + size - 1) // size)
    page = int(argument) if argument and argument.isdecimal() else 1
    page = min(max(page, 1), pages)
    start = (page - 1) * size
    return page, items[start : start + size], pages


def _date(value: str) -> str:
    return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y %H:%M")


def _memory_label(value: str) -> str:
    labels = {
        "fact": "fact",
        "preference": "preference",
        "event": "event",
        "pattern": "pattern",
        "hypothesis": "hypothesis",
    }
    return labels.get(value, value)


def _status_label(value: str) -> str:
    labels = {
        "user_confirmed": "confirmed",
        "agent_hypothesis": "unconfirmed",
        "user_corrected": "corrected",
        "offered": "offered",
        "agreed": "agreed",
        "tried": "tried",
        "not_tried": "not tried",
        "stopped": "stopped",
    }
    return labels.get(value, value)


def _http_error_description(error: HTTPError) -> str:
    try:
        body = json.loads(error.read())
    except (OSError, json.JSONDecodeError):
        return f"HTTP {error.code}"
    if isinstance(body, dict) and isinstance(body.get("description"), str):
        return body["description"]
    return f"HTTP {error.code}"

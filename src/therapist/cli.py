"""Minimal command-line interface for chat and user-controlled memory."""

import argparse
import getpass
import json
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from therapist.auth import (
    AuthError,
    codex_model,
    load_credential,
    login_codex,
    logout_codex,
)
from therapist.chat import ChatSession
from therapist.memory import MemoryStore
from therapist.protocol import ProtocolError, ProtocolPack
from therapist.telegram import TelegramBot, TelegramChannel, TelegramError

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = ROOT / "protocols" / "transdiagnostic-v0.3.0"
TELEGRAM_SECRET = "telegram_bot_token"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thera", description="Experimental AI conversation CLI")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.getenv("THERA_DATA_DIR", Path.home() / ".therapist")),
        help="Encrypted local memory directory (default: ~/.therapist)",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(os.getenv("THERA_PROTOCOL_PATH", DEFAULT_PROTOCOL)),
        help="Protocol pack directory",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("setup", help="Configure the harness interactively")

    chat = commands.add_parser("chat", help="Start an interactive conversation")
    chat.add_argument("--model")
    chat.add_argument("--locale", choices=("it-IT", "en-US"))

    telegram = commands.add_parser("telegram", help="Run a private single-user Telegram bot")
    telegram.add_argument("--model")
    telegram.add_argument("--locale", choices=("it-IT", "en-US"))
    telegram.add_argument("--allowed-user-id", type=int)

    auth = commands.add_parser("auth", help="Manage experimental ChatGPT Codex login")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)
    auth_commands.add_parser("login")
    auth_commands.add_parser("status")
    auth_commands.add_parser("logout")

    memory = commands.add_parser("memory", help="Inspect or edit longitudinal memory")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)
    memory_commands.add_parser("show")
    memory_commands.add_parser("case")
    memory_commands.add_parser("sessions")
    confirm = memory_commands.add_parser("confirm")
    confirm.add_argument("id")
    correct = memory_commands.add_parser("correct")
    correct.add_argument("id")
    correct.add_argument("text")
    forget = memory_commands.add_parser("forget")
    forget.add_argument("id")

    export = commands.add_parser("export", help="Export decrypted user-owned data as JSON")
    export.add_argument("--output", type=Path)
    delete = commands.add_parser("delete-data", help="Delete conversation and structured memory")
    delete.add_argument("--yes", action="store_true")
    commands.add_parser("doctor", help="Check local configuration without contacting a model")

    protocol = commands.add_parser("protocol", help="Protocol-pack utilities")
    protocol_commands = protocol.add_subparsers(dest="protocol_command", required=True)
    validate = protocol_commands.add_parser("validate")
    validate.add_argument("path", nargs="?", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pack = ProtocolPack.load(args.protocol)
    except ProtocolError as error:
        print(f"Protocol error: {error}")
        return 2

    if args.command == "protocol":
        path = args.path or args.protocol
        try:
            validated = ProtocolPack.load(path)
        except ProtocolError as error:
            print(f"Protocol error: {error}")
            return 2
        print(f"OK {validated.id} v{validated.version} ({validated.status})")
        return 0

    database_exists = (args.data_dir / "thera.db").exists()
    if args.command == "doctor":
        store = MemoryStore(args.data_dir) if database_exists else None
        state = store.load_app_state() if store else None
        model = (state.default_model if state else None) or "not configured"
        memory = "initialized" if database_exists else "not initialized"
        print(f"Protocol: {pack.id} v{pack.version} ({pack.status})")
        print(f"Memory: {args.data_dir} ({memory})")
        print(f"Model: {model}")
        telegram = "configured" if store and _telegram_config(store) else "not configured"
        print(f"Telegram: {telegram}")
        return 0

    store = MemoryStore(args.data_dir)
    if args.command == "setup":
        return _setup(store)
    if args.command == "auth":
        return _auth(args, store)
    if args.command in {"chat", "telegram"}:
        state = store.load_app_state()
        selected_model = args.model or state.default_model
        if not selected_model and load_credential(store):
            selected_model = "codex:gpt-5.5"
        if not selected_model:
            print("Missing model. Run `thera setup` or pass --model.")
            return 2
        locale = args.locale or state.default_locale or "en-US"
        try:
            model = (
                codex_model(store, selected_model.removeprefix("codex:"))
                if selected_model.startswith("codex:")
                else selected_model
            )
        except AuthError as error:
            print(f"Authentication error: {error}")
            return 2
        session = ChatSession(model, pack, store, locale)
        if args.command == "chat":
            return _chat(session, store, locale)
        token_payload = store.load_secret(TELEGRAM_SECRET)
        token = token_payload.decode() if token_payload else ""
        if not token:
            print("Telegram is not configured. Run `thera setup`.")
            return 2
        allowed_user_id = args.allowed_user_id or state.telegram_allowed_user_id
        if not allowed_user_id or allowed_user_id <= 0:
            print("Telegram is not configured. Run `thera setup`.")
            return 2
        try:
            TelegramChannel(
                TelegramBot(token), session, store, allowed_user_id, locale
            ).run()
        except TelegramError as error:
            print(f"Telegram startup error: {error}")
            return 2
        except KeyboardInterrupt:
            print()
        return 0
    if args.command == "memory":
        return _memory(args, store)
    if args.command == "export":
        content = json.dumps(store.export(), ensure_ascii=False, separators=(",", ":"))
        if args.output:
            args.output.write_text(content + "\n", encoding="utf-8")
            print(f"Exported to {args.output}")
        else:
            print(content)
        return 0
    if args.command == "delete-data":
        confirmed = args.yes or input(
            "Delete all local conversation and memory data? [y/N] "
        ).lower() == "y"
        if not confirmed:
            print("Cancelled.")
            return 1
        store.delete_all()
        print("Local conversation and memory data deleted.")
        return 0
    return 2


def _setup(store: MemoryStore) -> int:
    state = store.load_app_state()
    try:
        model = input(f"Model [{state.default_model or 'required'}]: ").strip()
        model = model or state.default_model
        if not model:
            print("A model is required, for example ollama:qwen3:8b or codex:gpt-5.5.")
            return 2

        current_locale = state.default_locale or "en-US"
        locale = input(f"Locale (it-IT/en-US) [{current_locale}]: ").strip() or current_locale
        if locale not in {"it-IT", "en-US"}:
            print("Locale must be it-IT or en-US.")
            return 2

        has_telegram = _telegram_config(store)
        default_choice = "Y/n" if has_telegram else "y/N"
        choice = input(f"Configure Telegram? [{default_choice}]: ").strip().lower()
        configure_telegram = choice in {"y", "yes"} or (not choice and has_telegram)
        if configure_telegram:
            token = getpass.getpass("Telegram bot token (hidden; blank keeps current): ").strip()
            token_payload = token.encode() if token else store.load_secret(TELEGRAM_SECRET)
            if not token_payload:
                print("A Telegram bot token is required.")
                return 2
            current_id = state.telegram_allowed_user_id
            raw_user_id = input(f"Allowed Telegram user ID [{current_id or 'required'}]: ").strip()
            try:
                user_id = int(raw_user_id) if raw_user_id else current_id
            except ValueError:
                user_id = None
            if not user_id or user_id <= 0:
                print("Telegram user ID must be a positive integer.")
                return 2
            store.save_secret(TELEGRAM_SECRET, token_payload)
            state.telegram_allowed_user_id = user_id

        state.default_model = model
        state.default_locale = locale
        store.save_app_state(state)
        if model.startswith("codex:") and not load_credential(store):
            login_now = input("Log in with ChatGPT now? [Y/n]: ").strip().lower()
            if login_now not in {"n", "no"}:
                try:
                    login_codex(store)
                except AuthError as error:
                    print(f"Authentication error: {error}")
                    return 2
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        return 1

    print(f"Configuration saved securely in {store.directory}.")
    telegram = "configured" if _telegram_config(store) else "skipped"
    print(f"Model: {model}; locale: {locale}; Telegram: {telegram}")
    if model.startswith("codex:") and not load_credential(store):
        print("Next: run `thera auth login` for ChatGPT Codex access.")
    return 0


def _telegram_config(store: MemoryStore) -> bool:
    state = store.load_app_state()
    return bool(store.load_secret(TELEGRAM_SECRET) and state.telegram_allowed_user_id)


def _auth(args: argparse.Namespace, store: MemoryStore) -> int:
    try:
        if args.auth_command == "login":
            credential = login_codex(store)
            print(f"Logged in with ChatGPT Codex account {credential.account_id}.")
        elif args.auth_command == "status":
            credential = load_credential(store)
            if credential is None:
                print("Not logged in.")
                return 1
            expires = datetime.fromtimestamp(credential.expires_at, UTC).isoformat()
            print(f"Logged in with ChatGPT Codex account {credential.account_id}.")
            print(f"Access token expires: {expires} (refresh is automatic)")
        elif args.auth_command == "logout":
            logout_codex(store)
            print("ChatGPT Codex credentials deleted.")
    except AuthError as error:
        print(f"Authentication error: {error}")
        return 2
    return 0


def _memory(args: argparse.Namespace, store: MemoryStore) -> int:
    try:
        if args.memory_command == "show":
            print(_json([item.model_dump(mode="json") for item in store.list_memory(True)]))
        elif args.memory_command == "case":
            print(store.load_formulation().model_dump_json(indent=2))
        elif args.memory_command == "sessions":
            print(_json([session.model_dump() for session in store.list_sessions()]))
        elif args.memory_command == "confirm":
            print(store.confirm_memory(args.id).model_dump_json(indent=2))
        elif args.memory_command == "correct":
            print(store.correct_memory(args.id, args.text).model_dump_json(indent=2))
        elif args.memory_command == "forget":
            print(store.forget_memory(args.id).model_dump_json(indent=2))
    except (KeyError, ValueError) as error:
        print(str(error))
        return 2
    return 0


def _chat(session: ChatSession, store: MemoryStore, locale: str) -> int:
    state = store.load_app_state()
    consent = "I UNDERSTAND" if locale == "en-US" else "CAPISCO"
    if state.consent_version != "alpha-1":
        notice = (
            "I am an experimental AI, not a therapist or emergency service. "
            "A remote model provider receives your messages when configured."
            if locale == "en-US"
            else "Sono un'AI sperimentale, non un terapeuta o un servizio di emergenza. "
            "Se configuri un provider remoto, quel provider riceve i tuoi messaggi."
        )
        print(notice)
        if input(f"Type {consent} to continue: ").strip() != consent:
            print("Consent not recorded.")
            return 1
        state.consent_version = "alpha-1"
        store.save_app_state(state)

    print("Commands: /case, /memory, /sessions [id], /confirm <id>, /correct <id> <text>,")
    print("          /forget <id>, /end, /help, /quit")
    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user_text:
            continue
        if user_text == "/quit":
            return 0
        if user_text.startswith("/"):
            if _chat_command(user_text, session, store):
                continue
            print("Unknown command. Use /help.")
            continue
        try:
            turn = session.respond(user_text)
        except Exception as error:  # Provider SDKs expose different error types.
            print(f"Model error: {error}")
            continue
        print(f"thera> {turn.text}")


def _chat_command(command: str, session: ChatSession, store: MemoryStore) -> bool:
    parts = command.split(maxsplit=2)
    name = parts[0]
    try:
        if name == "/help":
            print("/case /memory /sessions [id] /confirm <id> /correct <id> <text>")
            print("/forget <id> /end /quit")
        elif name == "/case":
            print(store.load_formulation().model_dump_json(indent=2))
        elif name == "/memory":
            print(_json([item.model_dump(mode="json") for item in store.list_memory(True)]))
        elif name == "/sessions":
            sessions = store.list_sessions()
            if len(parts) == 1:
                print(_json([item.model_dump() for item in sessions]))
            else:
                found = next((item for item in sessions if item.id == parts[1]), None)
                print("Session not found." if found is None else found.model_dump_json(indent=2))
        elif name == "/confirm" and len(parts) >= 2:
            print(store.confirm_memory(parts[1]).model_dump_json(indent=2))
        elif name == "/correct" and len(parts) == 3:
            print(store.correct_memory(parts[1], parts[2]).model_dump_json(indent=2))
        elif name == "/forget" and len(parts) >= 2:
            print(store.forget_memory(parts[1]).model_dump_json(indent=2))
        elif name == "/end":
            closed = session.end()
            message = (
                "No active session."
                if closed is None
                else "Session closed; transcript preserved."
            )
            print(message)
        else:
            return False
    except (KeyError, ValueError) as error:
        print(str(error))
    return True


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())

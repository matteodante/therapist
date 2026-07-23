import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic_ai import ModelRequest, ModelResponse, UserPromptPart
from pydantic_ai.messages import TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIResponsesModel

from therapist.chat import TurnStreamEvent, TurnStreamKind
from therapist.cli import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_REPO,
    DEFAULT_EMBEDDING_REVISION,
    _chat,
    _chat_command,
    _conversation_model,
    _ensure_chat_consent,
    _model_context_window,
    build_parser,
    main,
)
from therapist.memory import MemoryKind, MemoryObservation, MemoryStore


def test_chat_consent_discloses_scope_fallibility_and_data_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.consent_version = "alpha-1"
    store.save_app_state(state)
    monkeypatch.setattr("builtins.input", lambda _: "I UNDERSTAND")

    assert _ensure_chat_consent(store)

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Therapist is experimental AI" in output
    assert "at least 18" in output
    assert "output can be wrong" in output
    assert "selected context" in output
    assert store.load_app_state().consent_version == "alpha-2"


def test_openai_responses_storage_is_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    model = _conversation_model(MemoryStore(tmp_path), "openai:gpt-5.6-sol")

    assert isinstance(model, OpenAIResponsesModel)
    assert model.settings["openai_store"] is False


def test_hugging_face_telemetry_is_disabled() -> None:
    assert os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"
    assert os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] == "1"


def test_embedding_model_commands_manage_only_the_model_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    snapshot = tmp_path / "snapshot"
    revision = SimpleNamespace(
        commit_hash=DEFAULT_EMBEDDING_REVISION,
        refs={"main"},
        last_modified=1,
        snapshot_path=snapshot,
        size_on_disk=1024,
    )
    model = SimpleNamespace(
        repo_type="model",
        repo_id=DEFAULT_EMBEDDING_REPO,
        repo_path=tmp_path / "cache" / "model",
        size_on_disk=1024,
        revisions=[revision],
    )

    class Strategy:
        expected_freed_size_str = "1.0 KB"
        executed = False

        def execute(self) -> None:
            self.executed = True

    strategy = Strategy()
    cache = SimpleNamespace(
        delete_revisions=lambda *revisions: (
            strategy if revisions == (DEFAULT_EMBEDDING_REVISION,) else None
        )
    )
    monkeypatch.setattr("therapist.cli._embedding_cache_info", lambda: (cache, model, []))

    prefix = ["--data-dir", str(tmp_path), "memory", "model"]
    assert main([*prefix, "status"]) == 0
    assert main([*prefix, "remove", "--yes"]) == 0

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Status: installed" in output
    assert DEFAULT_EMBEDDING_REVISION in output
    assert "Encrypted memory data was not changed" in output
    assert strategy.executed
    assert not (tmp_path / "thera.db").exists()


def test_embedding_model_verify_checks_checksums_and_local_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    revision = SimpleNamespace(
        commit_hash=DEFAULT_EMBEDDING_REVISION,
        refs={"main"},
        last_modified=1,
        snapshot_path=tmp_path / "snapshot",
        size_on_disk=1024,
    )
    model = SimpleNamespace(revisions=[revision])
    result = SimpleNamespace(mismatches=[], checked_count=11)
    monkeypatch.setattr(
        "therapist.cli._embedding_cache_info",
        lambda: (SimpleNamespace(), model, []),
    )
    monkeypatch.setattr(
        "therapist.cli.HfApi",
        lambda: SimpleNamespace(verify_repo_checksums=lambda *args, **kwargs: result),
    )
    inferred_models: list[object] = []
    monkeypatch.setattr(
        "therapist.cli._verify_embedding_inference",
        lambda embedder: inferred_models.append(embedder) or 1024,
    )

    assert main(["memory", "model", "verify"]) == 0

    assert len(inferred_models) == 1
    assert "11 files, 1024 dimensions" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_embedding_model_install_uses_setup_smoke_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    prepared: list[bool] = []
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.embedding_model = "old:model"
    store.save_app_state(state)
    monkeypatch.setattr(
        "therapist.cli._prepare_semantic_memory",
        lambda: prepared.append(True) or True,
    )
    monkeypatch.setattr("therapist.cli._print_embedding_model_status", lambda: True)

    assert main(["--data-dir", str(tmp_path), "memory", "model", "install"]) == 0

    assert prepared == [True]
    assert MemoryStore(tmp_path).load_app_state().embedding_model == DEFAULT_EMBEDDING_MODEL
    assert "configuration updated" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_memory_commands_expose_and_correct_structured_memory(
    tmp_path: Path, capsys: object
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "I avoid calls", "What happens?", [])
    item = store.add_observations(
        [MemoryObservation(kind=MemoryKind.HYPOTHESIS, content="Calls trigger anxiety")],
        message_id,
    )[0]

    assert main(["--data-dir", str(tmp_path), "memory", "confirm", item.id]) == 0
    assert (
        main(
            [
                "--data-dir",
                str(tmp_path),
                "memory",
                "correct",
                item.id,
                "Some calls trigger anxiety",
            ]
        )
        == 0
    )
    assert main(["--data-dir", str(tmp_path), "memory", "show"]) == 0

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Some calls trigger anxiety" in output
    assert "user_corrected" in output


def test_interactive_command_and_output_stay_out_of_transcript(
    tmp_path: Path, capsys: object
) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    message_id = store.save_turn(session, "Original user turn.", "Original reply.", [])
    store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="Rendered command output.")],
        message_id,
    )
    before = store.session_transcript(session.id)

    assert _chat_command("/memory", SimpleNamespace(), store) is True  # type: ignore[arg-type]

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Rendered command output." in output
    assert store.session_transcript(session.id) == before
    assert "Rendered command output." not in before


def test_interactive_chat_prints_tool_input_and_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.consent_version = "alpha-2"
    store.save_app_state(state)
    inputs = iter(["Please remember this.", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    def respond(_: str, *, on_event: object) -> SimpleNamespace:
        on_event(  # type: ignore[operator]
            TurnStreamEvent(
                TurnStreamKind.TOOL_INPUT,
                'TOOL INPUT · record_memory\n{"content": "detail"}',
            )
        )
        on_event(  # type: ignore[operator]
            TurnStreamEvent(
                TurnStreamKind.TOOL_OUTPUT,
                'TOOL OUTPUT · record_memory · success\n{"staged": 1}',
            )
        )
        on_event(  # type: ignore[operator]
            TurnStreamEvent(TurnStreamKind.REPLY, "Done.")
        )
        return SimpleNamespace(text="Done.", notice=None, tool_trace=None)

    session = SimpleNamespace(respond=respond)

    assert _chat(session, store) == 0  # type: ignore[arg-type]

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "TOOL INPUT · record_memory" in output
    assert '"content": "detail"' in output
    assert "TOOL OUTPUT · record_memory · success" in output
    assert output.index("TOOL INPUT") < output.index("thera> Done.")


def test_plain_chat_does_not_persist_rejected_draft_in_redirected_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.consent_version = "alpha-2"
    store.save_app_state(state)
    inputs = iter(["Please answer.", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    def respond(_: str, *, on_event: object) -> SimpleNamespace:
        on_event(TurnStreamEvent(TurnStreamKind.REPLY, "rejected draft"))  # type: ignore[operator]
        on_event(TurnStreamEvent(TurnStreamKind.REPLY, "Validated reply."))  # type: ignore[operator]
        return SimpleNamespace(text="Validated reply.", notice=None)

    assert _chat(SimpleNamespace(respond=respond), store) == 0  # type: ignore[arg-type]

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "rejected draft" not in output
    assert output.count("thera> Validated reply.") == 1


def test_plain_chat_replaces_draft_in_interactive_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.consent_version = "alpha-2"
    store.save_app_state(state)
    inputs = iter(["Please answer.", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    updates: list[str] = []

    class FakeConsole:
        is_terminal = True

        def print(self, _: str) -> None:
            pass

    class FakeLive:
        def __init__(self, _: str, *, console: object, **_kwargs: object) -> None:
            self.console = console

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def update(self, text: str, *, refresh: bool) -> None:
            assert refresh
            updates.append(text)

    def respond(_: str, *, on_event: object) -> SimpleNamespace:
        on_event(TurnStreamEvent(TurnStreamKind.REPLY, "rejected draft"))  # type: ignore[operator]
        on_event(TurnStreamEvent(TurnStreamKind.REPLY, "Validated reply."))  # type: ignore[operator]
        return SimpleNamespace(text="Validated reply.", notice=None)

    monkeypatch.setattr("therapist.cli.Console", FakeConsole)
    monkeypatch.setattr("therapist.cli.Live", FakeLive)

    assert _chat(SimpleNamespace(respond=respond), store) == 0  # type: ignore[arg-type]
    assert updates == ["thera> rejected draft", "thera> Validated reply."]


def test_export_outputs_all_user_owned_layers(tmp_path: Path, capsys: object) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    store.save_turn(
        session,
        "Busy month",
        "What made it busy?",
        [
            ModelRequest(parts=[UserPromptPart(content="Busy month")]),
            ModelResponse(
                parts=[
                    ToolCallPart(
                        "record_memory",
                        {"content": "Busy month"},
                        tool_call_id="record",
                    )
                ]
            ),
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "record_memory",
                        {"staged": 1},
                        tool_call_id="record",
                    )
                ]
            ),
            ModelResponse(parts=[TextPart(content="What made it busy?")]),
        ],
    )

    assert main(["--data-dir", str(tmp_path), "export"]) == 0

    exported = json.loads(capsys.readouterr().out.splitlines()[-1])  # type: ignore[attr-defined]
    assert exported["messages"][0]["content"] == "Busy month"
    assert exported["sessions"][0]["id"] == session.id
    assert exported["messages"][1]["tool_exchanges"] == [
        {
            "direction": "input",
            "tool_name": "record_memory",
            "content": {"content": "Busy month"},
        },
        {
            "direction": "output",
            "tool_name": "record_memory",
            "content": {"staged": 1},
            "outcome": "success",
        },
    ]
    assert "case_formulation" in exported
    assert "interventions" in exported


def test_doctor_does_not_create_memory(tmp_path: Path) -> None:
    data_dir = tmp_path / "not-created"

    assert main(["--data-dir", str(data_dir), "doctor"]) == 0
    assert not data_dir.exists()


def test_context_window_override_is_bounded() -> None:
    parsed = build_parser().parse_args(
        ["chat", "--model", "test:model", "--context-window-tokens", "128000"]
    )

    assert parsed.context_window_tokens == 128_000
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["chat", "--model", "test:model", "--context-window-tokens", "128001"]
        )


def test_ollama_context_window_is_detected_and_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self) -> bytes:
            return json.dumps({"model_info": {"model.context_length": 262_144}}).encode()

    monkeypatch.setattr("therapist.cli.urlopen", lambda *args, **kwargs: Response())

    assert _model_context_window("ollama:test") == 128_000


def test_ollama_conversation_is_forced_to_loopback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.default_model = "ollama:test"
    state.default_context_window_tokens = 32_000
    state.default_locale = "en-US"
    state.embedding_model = DEFAULT_EMBEDDING_MODEL
    state.consent_version = "alpha-2"
    store.save_app_state(state)
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr("therapist.cli._default_embedder", lambda **_: object())
    monkeypatch.setattr("therapist.cli.ChatSession", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("therapist.cli._chat", lambda *_: 0)

    assert main(["--data-dir", str(tmp_path), "chat", "--plain"]) == 0
    assert os.environ["OLLAMA_BASE_URL"] == "http://localhost:11434/v1"


def test_context_override_cannot_exceed_saved_model_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.default_model = "test:model"
    state.default_context_window_tokens = 32_000
    state.default_locale = "en-US"
    state.embedding_model = DEFAULT_EMBEDDING_MODEL
    store.save_app_state(state)
    captured: dict[str, int] = {}

    def chat_session(*args: object, context_window_tokens: int, **kwargs: object) -> object:
        captured["context_window_tokens"] = context_window_tokens
        return object()

    monkeypatch.setattr("therapist.cli._default_embedder", lambda **_: object())
    monkeypatch.setattr("therapist.cli.ChatSession", chat_session)
    monkeypatch.setattr("therapist.cli._chat", lambda *_: 0)

    assert (
        main(
            [
                "--data-dir",
                str(tmp_path),
                "chat",
                "--context-window-tokens",
                "64000",
            ]
        )
        == 0
    )
    assert captured["context_window_tokens"] == 32_000


def test_tui_preloads_embedding_model_before_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.default_model = "test:model"
    state.embedding_model = DEFAULT_EMBEDDING_MODEL
    state.consent_version = "alpha-2"
    store.save_app_state(state)
    embedder = object()
    verified: list[object] = []

    monkeypatch.setattr("therapist.cli._uses_tui", lambda _: True)
    monkeypatch.setattr("therapist.cli._default_embedder", lambda **_: embedder)
    monkeypatch.setattr(
        "therapist.cli._verify_embedding_inference",
        lambda value: verified.append(value) or 1024,
    )
    monkeypatch.setattr("therapist.cli.ChatSession", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("therapist.cli._chat_tui", lambda *_: 0)

    assert main(["--data-dir", str(tmp_path), "chat"]) == 0
    assert verified == [embedder]


def test_telegram_service_install_uses_saved_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.default_model = "test:model"
    state.default_locale = "en-US"
    state.embedding_model = DEFAULT_EMBEDDING_MODEL
    state.telegram_allowed_user_id = 42
    store.save_secret("telegram_bot_token", b"secret")
    store.save_app_state(state)
    captured: list[tuple[list[str], Path]] = []
    monkeypatch.setattr(
        "therapist.cli.telegram_service.install",
        lambda command, data_dir: (
            captured.append((command, data_dir)) or tmp_path / "service.plist"
        ),
    )
    monkeypatch.setattr("therapist.cli.sys.argv", [str(tmp_path / "thera")])
    (tmp_path / "thera").write_text("#!/bin/sh\n")
    (tmp_path / "thera").chmod(0o755)

    assert main(["--data-dir", str(tmp_path), "telegram-service", "install"]) == 0

    command, data_dir = captured[0]
    assert command[0] == str((tmp_path / "thera").resolve())
    assert command[-1] == "telegram"
    assert command[1:3] == ["--data-dir", str(tmp_path.resolve())]
    assert data_dir == tmp_path.resolve()
    assert "installed and started" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_telegram_service_status_does_not_create_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    monkeypatch.setattr(
        "therapist.cli.telegram_service.status",
        lambda: SimpleNamespace(installed=False, running=False, detail=""),
    )

    assert main(["--data-dir", str(tmp_path), "telegram-service", "status"]) == 1

    assert not (tmp_path / "thera.db").exists()
    assert "Installed: no" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_semantic_memory_is_mandatory_for_conversation_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_models: list[str | None] = []

    def memory_store(directory: Path, *, embedding_model: str | None = None) -> MemoryStore:
        configured_models.append(embedding_model)
        return MemoryStore(directory)

    monkeypatch.setattr("therapist.cli.MemoryStore", memory_store)

    assert main(["--data-dir", str(tmp_path), "telegram", "--model", "test"]) == 2
    assert configured_models == [None]
    with pytest.raises(SystemExit):
        build_parser().parse_args(["chat", "--model", "test", "--no-semantic-memory"])


def test_telegram_fails_closed_without_channel_credentials(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.default_model = "test"
    state.default_locale = "en-US"
    state.embedding_model = DEFAULT_EMBEDDING_MODEL
    store.save_app_state(state)
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli._default_embedder", lambda **_: object()
    )
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_ID", raising=False)  # type: ignore[attr-defined]

    assert main(["--data-dir", str(tmp_path), "telegram", "--model", "test"]) == 2
    assert "Run `thera setup`" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_setup_stops_when_semantic_memory_cannot_be_prepared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("therapist.cli._prepare_semantic_memory", lambda: False)

    assert main(["--data-dir", str(tmp_path), "setup"]) == 2
    assert not (tmp_path / "thera.db").exists()
    assert not (tmp_path / "memory.key").exists()


def test_setup_saves_encrypted_defaults_used_by_telegram(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    selections = iter(["test", "en-US", True, True, False])
    monkeypatch.setattr("therapist.cli._prepare_semantic_memory", lambda: True)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.questionary.select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: next(selections)})(),
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.questionary.text",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: kwargs["default"]})(),
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.questionary.password",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: "secret-bot-token"})(),
    )
    monkeypatch.setattr("therapist.cli.secrets.token_urlsafe", lambda _: "pair-code")  # type: ignore[attr-defined]

    class PairingBot:
        def __init__(self, token: str) -> None:
            assert token == "secret-bot-token"

        def get_me(self) -> dict[str, str]:
            return {"username": "test_therapist_bot"}

        def delete_webhook(self) -> None:
            pass

        def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict]:
            if offset == -1:
                return []
            return [
                {
                    "update_id": 7,
                    "message": {
                        "from": {"id": 42, "first_name": "Test", "is_bot": False},
                        "chat": {"id": 42, "type": "private"},
                        "text": "/start pair-code",
                    },
                }
            ]

    monkeypatch.setattr("therapist.cli.TelegramBot", PairingBot)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.TelegramChannel.run", lambda _: None
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli._default_embedder", lambda **_: object()
    )
    monkeypatch.delenv("THERA_MODEL", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("THERA_LOCALE", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_ID", raising=False)  # type: ignore[attr-defined]

    assert main(["--data-dir", str(tmp_path), "setup"]) == 0
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    assert state.default_model == "test"
    assert state.default_context_window_tokens == 128_000
    assert state.default_locale == "en-US"
    assert state.embedding_model == DEFAULT_EMBEDDING_MODEL
    assert state.telegram_allowed_user_id == 42
    assert store.load_secret("telegram_bot_token") == b"secret-bot-token"
    assert "secret-bot-token" not in json.dumps(store.export())
    assert b"secret-bot-token" not in store.database_path.read_bytes()

    assert main(["--data-dir", str(tmp_path), "telegram"]) == 0
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Configuration saved securely" in output


def test_setup_can_install_telegram_background_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    selections = iter(["test", "en-US", True, True, True])
    monkeypatch.setattr("therapist.cli._prepare_semantic_memory", lambda: True)
    monkeypatch.setattr(
        "therapist.cli.questionary.select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: next(selections)})(),
    )
    monkeypatch.setattr(
        "therapist.cli.questionary.text",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: kwargs["default"]})(),
    )
    monkeypatch.setattr(
        "therapist.cli.questionary.password",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: "secret-bot-token"})(),
    )
    monkeypatch.setattr("therapist.cli.secrets.token_urlsafe", lambda _: "pair-code")

    class PairingBot:
        def __init__(self, _: str) -> None:
            pass

        def get_me(self) -> dict[str, str]:
            return {"username": "test_bot"}

        def delete_webhook(self) -> None:
            pass

        def get_updates(self, offset: int | None, timeout: int = 30) -> list[dict]:
            if offset == -1:
                return []
            return [
                {
                    "update_id": 7,
                    "message": {
                        "from": {"id": 42, "first_name": "Test", "is_bot": False},
                        "chat": {"id": 42, "type": "private"},
                        "text": "/start pair-code",
                    },
                }
            ]

    installed: list[list[str]] = []
    executable = tmp_path / "thera"
    executable.write_text("#!/bin/sh\n")
    executable.chmod(0o755)
    monkeypatch.setattr("therapist.cli.TelegramBot", PairingBot)
    monkeypatch.setattr("therapist.cli.sys.argv", [str(executable)])
    monkeypatch.setattr(
        "therapist.cli.telegram_service.install",
        lambda command, _: installed.append(command) or "native service",
    )

    assert main(["--data-dir", str(tmp_path), "setup"]) == 0

    assert installed[0][-1] == "telegram"
    assert "background service installed and started" in capsys.readouterr().out


def test_setup_stores_remote_provider_key_encrypted(tmp_path: Path, monkeypatch: object) -> None:
    selections = iter(["openai:gpt-5.6-sol", "en-US", False])
    monkeypatch.setattr("therapist.cli._prepare_semantic_memory", lambda: True)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.questionary.select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: next(selections)})(),
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.questionary.text",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: kwargs["default"]})(),
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.questionary.password",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: "private-api-key"})(),
    )

    assert main(["--data-dir", str(tmp_path), "setup"]) == 0

    store = MemoryStore(tmp_path)
    assert store.load_secret("openai_api_key") == b"private-api-key"
    assert store.load_app_state().embedding_model == DEFAULT_EMBEDDING_MODEL
    assert "private-api-key" not in json.dumps(store.export())
    assert b"private-api-key" not in store.database_path.read_bytes()


def test_setup_displays_and_overwrites_saved_context_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    state.default_model = "test"
    state.default_context_window_tokens = 32_000
    state.default_locale = "en-US"
    store.save_app_state(state)
    selections = iter(["test", "en-US", False])
    context_prompt: dict[str, object] = {}
    monkeypatch.setattr("therapist.cli._prepare_semantic_memory", lambda: True)
    monkeypatch.setattr(
        "therapist.cli.questionary.select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: next(selections)})(),
    )

    def text_prompt(*args: object, **kwargs: object) -> object:
        context_prompt.update(kwargs)
        return type("Prompt", (), {"ask": lambda _: "64000"})()

    monkeypatch.setattr("therapist.cli.questionary.text", text_prompt)

    assert main(["--data-dir", str(tmp_path), "setup"]) == 0

    saved = MemoryStore(tmp_path).load_app_state()
    assert context_prompt["default"] == "32000"
    assert "16000-128000" in str(context_prompt["instruction"])
    assert saved.default_context_window_tokens == 64_000


def test_setup_does_not_persist_provider_secret_when_later_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selections = iter(["openai:gpt-5.6-sol", None])
    monkeypatch.setattr("therapist.cli._prepare_semantic_memory", lambda: True)
    monkeypatch.setattr(
        "therapist.cli.questionary.select",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: next(selections)})(),
    )
    monkeypatch.setattr(
        "therapist.cli.questionary.password",
        lambda *args, **kwargs: type("Prompt", (), {"ask": lambda _: "must-not-persist"})(),
    )

    assert main(["--data-dir", str(tmp_path), "setup"]) == 1
    store = MemoryStore(tmp_path)
    assert store.load_secret("openai_api_key") is None
    assert store.load_app_state().default_model is None

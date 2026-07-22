import json
from pathlib import Path

from therapist.cli import main
from therapist.memory import MemoryKind, MemoryObservation, MemoryStore


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


def test_export_outputs_all_user_owned_layers(tmp_path: Path, capsys: object) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    store.save_turn(session, "Busy month", "What made it busy?", [])

    assert main(["--data-dir", str(tmp_path), "export"]) == 0

    exported = json.loads(capsys.readouterr().out.splitlines()[-1])  # type: ignore[attr-defined]
    assert exported["messages"][0]["content"] == "Busy month"
    assert exported["sessions"][0]["id"] == session.id
    assert "case_formulation" in exported


def test_doctor_does_not_create_memory(tmp_path: Path) -> None:
    data_dir = tmp_path / "not-created"

    assert main(["--data-dir", str(data_dir), "doctor"]) == 0
    assert not data_dir.exists()


def test_telegram_fails_closed_without_channel_credentials(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_ID", raising=False)  # type: ignore[attr-defined]

    assert (
        main(["--data-dir", str(tmp_path), "telegram", "--model", "test"])
        == 2
    )
    assert "Run `thera setup`" in capsys.readouterr().out  # type: ignore[attr-defined]


def test_setup_saves_encrypted_defaults_used_by_telegram(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    answers = iter(["test", "it-IT", "y", "42"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.getpass.getpass", lambda _: "secret-bot-token"
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "therapist.cli.TelegramChannel.run", lambda _: None
    )
    monkeypatch.delenv("THERA_MODEL", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("THERA_LOCALE", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_ID", raising=False)  # type: ignore[attr-defined]

    assert main(["--data-dir", str(tmp_path), "setup"]) == 0
    store = MemoryStore(tmp_path)
    state = store.load_app_state()
    assert state.default_model == "test"
    assert state.default_locale == "it-IT"
    assert state.telegram_allowed_user_id == 42
    assert store.load_secret("telegram_bot_token") == b"secret-bot-token"
    assert "secret-bot-token" not in json.dumps(store.export())
    assert b"secret-bot-token" not in store.database_path.read_bytes()

    assert main(["--data-dir", str(tmp_path), "telegram"]) == 0
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Configuration saved securely" in output

import plistlib
import subprocess
from pathlib import Path

import pytest

from therapist.telegram_service import (
    SERVICE_LABEL,
    SYSTEMD_UNIT,
    WINDOWS_TASK,
    TelegramServiceError,
    install,
    restart,
    status,
    uninstall,
)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], int] | None = None) -> None:
        self.commands: list[list[str]] = []
        self.responses = responses or {}

    def __call__(self, command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        code = self.responses.get(tuple(command), 0)
        return subprocess.CompletedProcess(command, code, stdout="active\n", stderr="")


def test_macos_service_install_status_and_uninstall(tmp_path: Path) -> None:
    runner = FakeRunner()
    home = tmp_path / "home"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    command = ["/opt/thera", "--data-dir", str(data_dir), "telegram"]

    path = install(command, data_dir, platform="darwin", home=home, runner=runner)

    payload = plistlib.loads(path.read_bytes())
    assert payload["Label"] == SERVICE_LABEL
    assert payload["ProgramArguments"] == command
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] is True
    assert path.stat().st_mode & 0o777 == 0o600
    assert status(platform="darwin", home=home, runner=runner).running is True
    assert uninstall(platform="darwin", home=home, runner=runner) is True
    assert not path.exists()


def test_linux_service_uses_user_systemd_and_quotes_arguments(tmp_path: Path) -> None:
    runner = FakeRunner()
    home = tmp_path / "home"
    data_dir = tmp_path / "data with spaces"
    data_dir.mkdir()
    command = ["/opt/thera app/thera", "--data-dir", str(data_dir), "telegram"]

    path = install(command, data_dir, platform="linux", home=home, runner=runner)

    unit = path.read_text()
    assert path.name == SYSTEMD_UNIT
    assert 'ExecStart="/opt/thera app/thera" "--data-dir"' in unit
    assert ["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT] in runner.commands
    assert uninstall(platform="linux", home=home, runner=runner) is True
    assert runner.commands[-1] == ["systemctl", "--user", "daemon-reload"]


def test_service_reports_native_manager_failure(tmp_path: Path) -> None:
    command = ["systemctl", "--user", "daemon-reload"]
    runner = FakeRunner({tuple(command): 1})

    with pytest.raises(TelegramServiceError, match="systemctl failed"):
        install(
            ["/opt/thera", "telegram"],
            tmp_path,
            platform="linux",
            home=tmp_path,
            runner=runner,
        )


def test_linux_service_rejects_control_characters_in_command(tmp_path: Path) -> None:
    with pytest.raises(TelegramServiceError, match="control characters"):
        install(
            ["/opt/thera", "--data-dir", "/tmp/data\n[Install]"],
            tmp_path,
            platform="linux",
            home=tmp_path,
            runner=FakeRunner(),
        )


def test_windows_task_install_status_restart_and_uninstall(tmp_path: Path) -> None:
    runner = FakeRunner()
    command = [
        r"C:\Program Files\Therapist\thera.exe",
        "--data-dir",
        r"C:\Users\Test User\Therapist",
        "telegram",
    ]

    location = install(command, tmp_path, platform="win32", runner=runner)

    create = runner.commands[0]
    assert location == f"Task Scheduler: {WINDOWS_TASK}"
    assert create[:4] == ["schtasks.exe", "/Create", "/TN", WINDOWS_TASK]
    assert create[create.index("/SC") + 1] == "ONLOGON"
    assert create[create.index("/RL") + 1] == "LIMITED"
    assert '"C:\\Program Files\\Therapist\\thera.exe"' in create[create.index("/TR") + 1]
    assert runner.commands[1] == ["schtasks.exe", "/Run", "/TN", WINDOWS_TASK]
    assert status(platform="win32", runner=runner).running is True

    restart(platform="win32", runner=runner)
    assert ["schtasks.exe", "/End", "/TN", WINDOWS_TASK] in runner.commands
    assert runner.commands[-1] == ["schtasks.exe", "/Run", "/TN", WINDOWS_TASK]

    assert uninstall(platform="win32", runner=runner) is True
    assert runner.commands[-1] == [
        "schtasks.exe",
        "/Delete",
        "/TN",
        WINDOWS_TASK,
        "/F",
    ]


def test_windows_uninstall_reports_missing_task(tmp_path: Path) -> None:
    status_command_prefix = ("powershell.exe", "-NoProfile", "-NonInteractive")

    class MissingTaskRunner(FakeRunner):
        def __call__(
            self, command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if tuple(command[:3]) == status_command_prefix:
                self.commands.append(command)
                return subprocess.CompletedProcess(command, 2, stdout="", stderr="")
            return super().__call__(command, **kwargs)

    runner = MissingTaskRunner()

    assert uninstall(platform="win32", runner=runner) is False
    assert all("/Delete" not in command for command in runner.commands)

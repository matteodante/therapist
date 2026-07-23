import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_macos_setup_runs_inside_a_fresh_pseudoterminal() -> None:
    installer = (ROOT / "install.sh").read_text()

    assert 'Darwin) script -q -e /dev/null "$THERA" setup </dev/tty ;;' in installer


def test_release_version_is_synchronized_across_installers() -> None:
    with (ROOT / "pyproject.toml").open("rb") as project_file:
        version = tomllib.load(project_file)["project"]["version"]

    assert f'THERAPIST_VERSION="v{version}"' in (ROOT / "install.sh").read_text()
    assert f'$TherapistVersion = "v{version}"' in (ROOT / "install.ps1").read_text()
    assert f'__version__ = "{version}"' in (ROOT / "src/therapist/__init__.py").read_text()

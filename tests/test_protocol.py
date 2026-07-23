from pathlib import Path

import pytest

from therapist.protocol import ProtocolError, ProtocolPack


def test_bundled_protocol_is_bilingual_git_versioned_and_experimental() -> None:
    root = Path("protocols/transdiagnostic")
    pack = ProtocolPack.load(root)

    assert pack.id == "therapist.transdiagnostic"
    assert pack.status == "experimental"
    assert set(pack.locales) == {"it-IT", "en-US"}
    assert len(pack.skills) == 6
    assert "version:" not in (root / "manifest.yaml").read_text(encoding="utf-8")
    assert "build-shared-formulation" in pack.instructions
    assert "do not claim to be a psychologist" in pack.instructions.casefold()
    assert "do not append routine" in pack.instructions.casefold()
    assert "explicitly says they are under 18" in pack.instructions.casefold()
    assert "never infer danger from a keyword alone" in pack.instructions.casefold()
    assert "repair-misattunement" in pack.instructions
    assert "Use state tools" in pack.instructions
    assert not list(Path("protocols").glob("transdiagnostic-v*"))


def test_manifest_version_is_rejected_in_favor_of_git_history(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("instructions", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        """id: test.pack
version: 1.2.3
status: experimental
locales: [en-US]
root_sha256: deadbeef
references: []
""",
        encoding="utf-8",
    )

    with pytest.raises(ProtocolError, match="tracked by Git"):
        ProtocolPack.load(tmp_path)


def test_changed_reference_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "references").mkdir()
    (tmp_path / "SKILL.md").write_text("instructions", encoding="utf-8")
    (tmp_path / "references" / "source.md").write_text("changed", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        """id: test.pack
status: experimental
locales: [it-IT]
root_sha256: 238fa28a94976c7da14563bc873c2729bd5cd325389085bb4c6dd0de28923590
references:
  - path: references/source.md
    sha256: deadbeef
    url: https://example.test
    revision: test
    license: test
""",
        encoding="utf-8",
    )

    with pytest.raises(ProtocolError, match="hash"):
        ProtocolPack.load(tmp_path)


def test_changed_skill_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()
    (tmp_path / "SKILL.md").write_text("root instructions", encoding="utf-8")
    (tmp_path / "skills" / "test.md").write_text("changed", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        """id: test.pack
status: experimental
locales: [en-US]
root_sha256: 16ffc8b69356ecb4270367c806b5397a633d824d9225065c332ae7c7095a5c5c
skills:
  - path: skills/test.md
    sha256: deadbeef
references: []
""",
        encoding="utf-8",
    )

    with pytest.raises(ProtocolError, match="skill hash"):
        ProtocolPack.load(tmp_path)


def test_changed_root_skill_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("changed", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        """id: test.pack
status: experimental
locales: [en-US]
root_sha256: deadbeef
references: []
""",
        encoding="utf-8",
    )

    with pytest.raises(ProtocolError, match="root skill hash"):
        ProtocolPack.load(tmp_path)

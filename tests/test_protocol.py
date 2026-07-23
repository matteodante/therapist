from pathlib import Path

import pytest

from therapist.protocol import ProtocolError, ProtocolPack


def test_bundled_protocol_is_bilingual_and_experimental() -> None:
    pack = ProtocolPack.load(Path("protocols/transdiagnostic-v0.5.0"))

    assert pack.id == "therapist.transdiagnostic"
    assert pack.version == "0.5.0"
    assert pack.status == "experimental"
    assert set(pack.locales) == {"it-IT", "en-US"}
    assert len(pack.skills) == 6
    assert "build-shared-formulation" in pack.instructions
    assert "do not claim to be a psychologist" in pack.instructions.casefold()
    assert "do not append routine" in pack.instructions.casefold()
    assert "repair-misattunement" in pack.instructions
    assert "Use state tools" in pack.instructions


def test_previous_protocol_pack_still_loads() -> None:
    assert ProtocolPack.load(Path("protocols/transdiagnostic-v0.4.0")).version == "0.4.0"


def test_legacy_pack_without_skills_still_loads() -> None:
    pack = ProtocolPack.load(Path("protocols/transdiagnostic-v0.2.0"))

    assert pack.version == "0.2.0"
    assert pack.skills == ()


def test_changed_reference_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "references").mkdir()
    (tmp_path / "SKILL.md").write_text("instructions", encoding="utf-8")
    (tmp_path / "references" / "source.md").write_text("changed", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        """id: test.pack
version: 0.1.0
status: experimental
locales: [it-IT]
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
version: 0.1.0
status: experimental
locales: [en-US]
skills:
  - path: skills/test.md
    sha256: deadbeef
references: []
""",
        encoding="utf-8",
    )

    with pytest.raises(ProtocolError, match="skill hash"):
        ProtocolPack.load(tmp_path)

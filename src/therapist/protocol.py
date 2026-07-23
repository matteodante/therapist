"""Git-versioned protocol-pack loader with path and hash validation."""

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class ProtocolError(RuntimeError):
    pass


class Reference(BaseModel):
    path: str
    sha256: str
    url: str
    revision: str
    license: str


class PackSkill(BaseModel):
    path: str
    sha256: str


class Manifest(BaseModel):
    id: str
    status: str
    locales: list[str]
    skills: list[PackSkill] = Field(default_factory=list)
    references: list[Reference]


class ProtocolPack:
    def __init__(self, manifest: Manifest, instructions: str, root: Path) -> None:
        self.id = manifest.id
        self.status = manifest.status
        self.locales = manifest.locales
        self.skills = tuple(skill.path for skill in manifest.skills)
        self.instructions = instructions
        self.root = root

    @classmethod
    def load(cls, root: Path) -> "ProtocolPack":
        root = root.resolve()
        try:
            raw = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "version" in raw:
                raise ProtocolError("Protocol revisions are tracked by Git, not manifest versions.")
            manifest = Manifest.model_validate(raw)
            root_instructions = (root / "SKILL.md").read_text(encoding="utf-8")
        except (OSError, ValidationError, yaml.YAMLError) as error:
            raise ProtocolError(f"Invalid protocol pack: {error}") from error
        if manifest.status not in {"experimental", "reviewed", "validated"}:
            raise ProtocolError("Invalid protocol status.")
        skill_instructions: list[str] = []
        for skill in manifest.skills:
            skill_instructions.append(
                _verified_file(root, skill.path, skill.sha256, "skill").decode("utf-8")
            )
        for reference in manifest.references:
            _verified_file(root, reference.path, reference.sha256, "reference")
        instructions = "\n\n".join([root_instructions, *skill_instructions])
        return cls(manifest, instructions, root)


def _verified_file(root: Path, relative_path: str, expected_hash: str, kind: str) -> bytes:
    path = (root / relative_path).resolve()
    if root not in path.parents:
        raise ProtocolError(f"A {kind} path escapes the protocol directory.")
    try:
        contents = path.read_bytes()
    except OSError as error:
        raise ProtocolError(f"Missing {kind}: {relative_path}") from error
    if hashlib.sha256(contents).hexdigest() != expected_hash:
        raise ProtocolError(f"Invalid {kind} hash: {relative_path}")
    return contents

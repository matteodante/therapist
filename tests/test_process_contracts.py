import tempfile
from pathlib import Path
from typing import Any

from pydantic_ai.models.test import TestModel
from pydantic_evals import Dataset
from pydantic_evals.evaluators import EqualsExpected

from therapist.chat import ChatSession
from therapist.memory import MemoryStore
from therapist.protocol import ProtocolPack

CASES_PATH = Path(__file__).parent / "cases" / "process_contracts.yaml"
PACK_PATH = Path("protocols/transdiagnostic-v0.4.0")


def test_deterministic_process_contracts(tmp_path: Path) -> None:
    loaded = Dataset[dict[str, Any], dict[str, Any], dict[str, Any]].from_file(CASES_PATH)

    def run_case(inputs: dict[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(dir=tmp_path) as directory:
            store = MemoryStore(Path(directory))
            turn = ChatSession(
                TestModel(custom_output_args=inputs["model_output"]),
                ProtocolPack.load(PACK_PATH),
                store,
                inputs["locale"],
            ).respond(inputs["user_text"])
            return {
                "completed": True,
                "memory_count": len(store.list_memory()),
                "process_stage": turn.process_stage.value,
            }

    dataset = Dataset(
        name=loaded.name,
        cases=loaded.cases,
        evaluators=[EqualsExpected()],
    )
    report = dataset.evaluate_sync(run_case, progress=False)

    assert not report.failures, report.render(include_errors=True)
    assert all(
        result.value
        for case in report.cases
        for result in case.assertions.values()
    ), report.render(include_input=True, include_output=True, include_reasons=True)

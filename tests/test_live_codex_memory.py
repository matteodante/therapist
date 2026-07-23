import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import models
from pydantic_evals import Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from therapist.auth import codex_model, load_credential
from therapist.chat import ChatSession
from therapist.cli import DEFAULT_EMBEDDING_MODEL
from therapist.memory import MemoryKind, MemoryStatus, MemoryStore
from therapist.protocol import ProtocolPack

CASES_PATH = Path(__file__).parent / "cases" / "live_codex_memory.yaml"
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("THERA_RUN_CODEX_EVALS") != "1",
        reason="Set THERA_RUN_CODEX_EVALS=1 after `thera auth login`.",
    ),
]


@dataclass
class CodexMemoryContract(Evaluator[dict[str, Any], dict[str, Any], dict[str, Any]]):
    def evaluate(
        self, ctx: EvaluatorContext[dict[str, Any], dict[str, Any], dict[str, Any]]
    ) -> dict[str, bool]:
        expected = ctx.expected_output or {}
        context = ctx.output["context"].casefold()
        reply = ctx.output["return_reply"].casefold()
        return {
            "durable_memory_created": (
                ctx.output["memory_count"] >= expected["minimum_memory_items"]
            ),
            "confirmed_hypothesis_recorded": (
                not expected["require_confirmed_hypothesis"]
                or ctx.output["confirmed_hypothesis_count"] > 0
            ),
            "evidence_provenance_preserved": ctx.output["evidence_preserved"],
            "session_consolidated": ctx.output["session_consolidated"],
            "semantic_context_retrieved": all(
                term.casefold() in context for term in expected["context_terms"]
            ),
            "semantic_index_complete": ctx.output["semantic_index_complete"],
            "return_uses_continuity": any(
                term.casefold() in reply for term in expected["continuity_terms"]
            ),
            "new_session_created": (
                ctx.output["session_count"] >= expected["minimum_sessions"]
            ),
            "return_reply_non_empty": bool(reply.strip()),
        }


def test_configured_codex_longitudinal_memory(tmp_path: Path) -> None:
    credential_store = MemoryStore()
    if load_credential(credential_store) is None:
        pytest.skip("Run `thera auth login` before the Codex memory eval.")
    model = codex_model(credential_store, "gpt-5.6-sol")
    pack = ProtocolPack.load(Path("protocols/transdiagnostic"))
    loaded = Dataset[dict[str, Any], dict[str, Any], dict[str, Any]].from_file(CASES_PATH)

    def run_case(inputs: dict[str, Any]) -> dict[str, Any]:
        started_at = datetime.fromisoformat(inputs["started_at"])
        with tempfile.TemporaryDirectory(dir=tmp_path) as data_directory:
            path = Path(data_directory)
            store = MemoryStore(path, embedding_model=DEFAULT_EMBEDDING_MODEL)
            chat = ChatSession(model, pack, store, "it-IT")
            replies = [
                chat.respond(
                    message, started_at + timedelta(minutes=index * 10)
                ).text
                for index, message in enumerate(inputs["initial_messages"])
            ]
            closed = chat.end(started_at + timedelta(hours=1))

            restarted = MemoryStore(path, embedding_model=DEFAULT_EMBEDDING_MODEL)
            context = restarted.working_context(inputs["semantic_query"])
            returned = ChatSession(model, pack, restarted, "it-IT").respond(
                inputs["return_message"],
                started_at + timedelta(days=inputs["return_after_days"]),
            )
            items = restarted.list_memory()
            restarted.working_context(inputs["return_message"])
            with sqlite3.connect(restarted.database_path) as database:
                indexed = database.execute(
                    "SELECT COUNT(*) FROM semantic_index"
                ).fetchone()[0]
            return {
                "memory_count": len(items),
                "confirmed_hypothesis_count": sum(
                    item.status is MemoryStatus.USER_CONFIRMED
                    and item.kind in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS}
                    for item in items
                ),
                "evidence_preserved": bool(items)
                and all(item.evidence_message_ids for item in items),
                "session_consolidated": (
                    closed is not None
                    and bool(closed.summary.strip())
                    and closed.consolidation_error is None
                ),
                "context": context.model_dump_json(),
                "semantic_index_complete": indexed >= len(items),
                "return_reply": returned.text,
                "session_count": len(restarted.list_sessions()),
                "initial_replies": replies,
            }

    dataset = Dataset(
        name=loaded.name,
        cases=loaded.cases,
        evaluators=[CodexMemoryContract()],
    )
    with models.override_allow_model_requests(True):
        report = dataset.evaluate_sync(
            run_case,
            repeat=int(os.getenv("THERA_CODEX_EVAL_REPEAT", "1")),
            progress=False,
        )

    failed = [
        f"{case.name}:{name}: {result.reason or 'no reason'}\n{case.output}"
        for case in report.cases
        for name, result in case.assertions.items()
        if not result.value
    ]
    assert not report.failures, report.render(include_errors=True)
    assert not failed, "\n\n".join(failed)

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pydantic_evals import Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from therapist.memory import MemoryKind, MemoryObservation, MemoryStore

CASES_PATH = Path(__file__).parent / "cases" / "longitudinal_memory.yaml"


@dataclass
class LongitudinalMemoryContract(Evaluator[dict[str, Any], dict[str, Any], dict[str, Any]]):
    def evaluate(
        self, ctx: EvaluatorContext[dict[str, Any], dict[str, Any], dict[str, Any]]
    ) -> dict[str, bool]:
        expected = ctx.expected_output or {}
        context = ctx.output["context"].casefold()
        expected_export_status = expected.get("export_status")
        return {
            "at_least_three_months": ctx.output["age_days"] >= 90,
            "required_memory_recalled": all(
                term.casefold() in context for term in expected["required_terms"]
            ),
            "superseded_or_forgotten_memory_absent": all(
                term.casefold() not in context for term in expected["forbidden_terms"]
            ),
            "memory_states_match": set(ctx.output["statuses"]) == set(expected["statuses"]),
            "evidence_provenance_preserved": ctx.output["evidence_preserved"],
            "completed_session_persisted": ctx.output["completed_session_persisted"],
            "sensitive_plaintext_absent": ctx.output["sensitive_plaintext_absent"],
            "archive_status_matches": expected_export_status is None
            or expected_export_status in ctx.output["export_statuses"],
        }


def _run_longitudinal_case(inputs: dict[str, Any]) -> dict[str, Any]:
    with TemporaryDirectory(prefix="therapist-eval-") as directory:
        path = Path(directory)
        store = MemoryStore(path)
        started_at = datetime.fromisoformat(inputs["started_at"])
        return_at = datetime.fromisoformat(inputs["return_at"])
        session = store.start_session(started_at)
        evidence_id = store.save_turn(
            session,
            inputs["user_message"],
            inputs["assistant_message"],
            [],
            started_at,
        )
        items = store.add_observations(
            [
                MemoryObservation(kind=MemoryKind(item["kind"]), content=item["content"])
                for item in inputs["observations"]
            ],
            evidence_id,
            started_at,
        )
        store.close_session(session, summary=inputs["summary"], now=started_at)

        operation = inputs.get("operation")
        if operation:
            target = next(item for item in items if item.content == operation["target"])
            if operation["type"] == "correct":
                store.correct_memory(target.id, operation["replacement"])
            else:
                store.forget_memory(target.id)

        restarted = MemoryStore(path)
        context = restarted.working_context(inputs["query"])
        active_items = context.confirmed_memory + context.hypotheses
        exported = restarted.export()
        exported_by_id = {item["id"]: item for item in exported["memory"]}
        sensitive_fragments = [
            inputs["user_message"].encode(),
            *(item["content"].encode() for item in inputs["observations"]),
        ]
        database = restarted.database_path.read_bytes()
        return {
            "age_days": (return_at - started_at).days,
            "context": context.model_dump_json(),
            "statuses": [item.status.value for item in active_items],
            "evidence_preserved": all(
                exported_by_id[item.id]["evidence_message_ids"] == [evidence_id]
                for item in active_items
            ),
            "completed_session_persisted": bool(
                context.recent_sessions and context.recent_sessions[0].ended_at
            ),
            "sensitive_plaintext_absent": all(
                fragment not in database for fragment in sensitive_fragments
            ),
            "export_statuses": [item["status"] for item in exported["memory"]],
        }


def test_written_longitudinal_dataset() -> None:
    loaded = Dataset[dict[str, Any], dict[str, Any], dict[str, Any]].from_file(CASES_PATH)
    dataset = Dataset(
        name=loaded.name,
        cases=loaded.cases,
        evaluators=[LongitudinalMemoryContract()],
    )

    report = dataset.evaluate_sync(_run_longitudinal_case, progress=False)
    failed = [
        f"{case.name}:{name}"
        for case in report.cases
        for name, result in case.assertions.items()
        if not result.value
    ]

    assert not report.failures, report.render(include_errors=True)
    assert not failed, report.render(include_input=True, include_output=True, include_reasons=True)


def test_longitudinal_context_stays_bounded_with_hundreds_of_records(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    for index in range(120):
        started_at = datetime.fromisoformat(f"2025-01-{index % 28 + 1:02d}T09:00:00+00:00")
        session = store.start_session(started_at)
        evidence_id = store.save_turn(
            session,
            f"Recurring workload record {index}",
            "Recorded.",
            [],
            started_at,
        )
        store.add_observations(
            [
                MemoryObservation(kind=MemoryKind.EVENT, content=f"Workload event {index}"),
                MemoryObservation(kind=MemoryKind.PATTERN, content=f"Workload pattern {index}"),
            ],
            evidence_id,
            started_at,
        )
        store.close_session(session, summary=f"Session {index} about workload", now=started_at)

    context = MemoryStore(tmp_path).working_context("recurring workload")

    assert len(context.confirmed_memory) == 30
    assert len(context.hypotheses) == 10
    assert len(context.recent_sessions) == 3
    assert len(context.relevant_excerpts) == 5
    assert len(context.model_dump_json()) < 30_000

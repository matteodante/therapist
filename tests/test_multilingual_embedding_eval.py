import os
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic_evals import Dataset
from pydantic_evals.evaluators import EqualsExpected

from therapist.cli import DEFAULT_EMBEDDING_MODEL, _default_embedder
from therapist.memory import (
    InterventionState,
    MemoryKind,
    MemoryObservation,
    MemoryStore,
)

CASES_PATH = Path(__file__).parent / "cases" / "multilingual_semantic_memory.yaml"
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("THERA_RUN_MULTILINGUAL_EMBEDDING_EVALS") != "1",
        reason=("Set THERA_RUN_MULTILINGUAL_EMBEDDING_EVALS=1 after `thera memory model install`."),
    ),
]


def test_real_multilingual_semantic_memory(tmp_path: Path) -> None:
    loaded = Dataset[dict[str, Any], dict[str, bool], Any].from_file(CASES_PATH)
    embedder = _default_embedder(local_files_only=True)
    case_offset = int(os.getenv("THERA_MULTILINGUAL_EVAL_OFFSET", "0"))
    case_limit = int(os.getenv("THERA_MULTILINGUAL_EVAL_LIMIT", "0"))
    selected_cases = loaded.cases[case_offset:]
    if case_limit:
        selected_cases = selected_cases[:case_limit]

    def run_case(inputs: dict[str, Any]) -> dict[str, bool]:
        started = datetime(2026, 1, 1, tzinfo=UTC)
        with tempfile.TemporaryDirectory(prefix="thera-multilingual-", dir=tmp_path) as directory:
            path = Path(directory)
            store = MemoryStore(path, embedding_model=DEFAULT_EMBEDDING_MODEL, embedder=embedder)
            session = store.start_session(started)
            relevant_message = store.save_turn(
                session, inputs["memory"], "Tell me more.", [], started
            )
            relevant = store.add_observations(
                [MemoryObservation(kind=MemoryKind.PATTERN, content=inputs["memory"])],
                relevant_message,
                started,
            )[0]
            relevant_intervention = store.create_intervention(
                skill="problem-solving",
                description=inputs["memory"],
                prediction=None,
                state=InterventionState.OFFERED,
                linked_memory_ids=[relevant.id],
                evidence_message_id=relevant_message,
                now=started,
            )
            for index, distractor in enumerate(inputs["distractors"], start=1):
                observed_at = started + timedelta(days=30 * index)
                message_id = store.save_turn(session, distractor, "Noted.", [], observed_at)
                item = store.add_observations(
                    [MemoryObservation(kind=MemoryKind.EVENT, content=distractor)],
                    message_id,
                    observed_at,
                )[0]
                if index == 1:
                    store.create_intervention(
                        skill="behavioral-change",
                        description=distractor,
                        prediction=None,
                        state=InterventionState.OFFERED,
                        linked_memory_ids=[item.id],
                        evidence_message_id=message_id,
                        now=observed_at,
                    )

            first = store.working_context(inputs["query"])
            restarted = MemoryStore(
                path, embedding_model=DEFAULT_EMBEDDING_MODEL, embedder=embedder
            )
            second = restarted.working_context(inputs["query"])
            with sqlite3.connect(store.database_path) as database:
                index_count = database.execute("SELECT COUNT(*) FROM semantic_index").fetchone()[0]
            database_bytes = store.database_path.read_bytes()
            expected_index_count = len(inputs["distractors"]) * 2 + 4
            return {
                "claim_ranked_first": first.hypotheses[0].id == relevant.id,
                "excerpt_ranked_first": first.relevant_excerpts[0] == inputs["memory"],
                "intervention_ranked_first": (
                    first.active_interventions[0].id == relevant_intervention.id
                ),
                "index_reused_after_restart": (
                    second.hypotheses[0].id == relevant.id and index_count == expected_index_count
                ),
                "encrypted_at_rest": all(
                    text.encode() not in database_bytes
                    for text in [inputs["memory"], *inputs["distractors"]]
                ),
            }

    dataset = Dataset(
        name=loaded.name,
        cases=selected_cases,
        evaluators=[EqualsExpected()],
    )
    report = dataset.evaluate_sync(run_case, max_concurrency=1, progress=False)

    assert not report.failures, report.render(include_errors=True)
    assert all(result.value for case in report.cases for result in case.assertions.values()), (
        report.render(include_input=True, include_output=True, include_reasons=True)
    )

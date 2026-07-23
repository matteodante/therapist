import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic_evals import Dataset
from pydantic_evals.evaluators import EqualsExpected

from therapist.memory import MemoryKind, MemoryObservation, MemoryStore

CASES_PATH = Path(__file__).parent / "cases" / "semantic_memory.yaml"


class BilingualConceptEmbedder:
    def __init__(self) -> None:
        self.document_calls = 0

    @staticmethod
    def _vector(text: str) -> list[float]:
        normalized = text.casefold()
        concepts = (
            ("responsabile", "telefonate", "manager", "delivery", "late"),
            ("sister", "guilt", "sorella", "colpa"),
            ("night", "sleep", "preoccupazione", "serale", "sveglio"),
        )
        for index, terms in enumerate(concepts):
            if any(term in normalized for term in terms):
                return [float(position == index) for position in range(4)]
        return [0.0, 0.0, 0.0, 1.0]

    def embed_documents_sync(self, documents: list[str]) -> SimpleNamespace:
        self.document_calls += 1
        return SimpleNamespace(embeddings=[self._vector(text) for text in documents])

    def embed_query_sync(self, query: str) -> SimpleNamespace:
        return SimpleNamespace(embeddings=[self._vector(query)])


def _run_semantic_case(inputs: dict[str, Any]) -> dict[str, bool]:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix="thera-semantic-eval-") as directory:
        path = Path(directory)
        embedder = BilingualConceptEmbedder()
        store = MemoryStore(  # type: ignore[arg-type]
            path, embedding_model="test:bilingual", embedder=embedder
        )
        started = datetime(2026, 1, 1, tzinfo=UTC)
        session = store.start_session(started)
        relevant_message = store.save_turn(
            session, inputs["memory"], "Tell me more.", [], started
        )
        relevant = store.add_observations(
            [MemoryObservation(kind=MemoryKind.EVENT, content=inputs["memory"])],
            relevant_message,
            started,
        )[0]
        distractor_message = store.save_turn(
            session,
            inputs["distractor"],
            "Noted.",
            [],
            started + timedelta(days=120),
        )
        store.add_observations(
            [MemoryObservation(kind=MemoryKind.EVENT, content=inputs["distractor"])],
            distractor_message,
            started + timedelta(days=120),
        )

        first_context = store.working_context(inputs["query"])
        restarted = MemoryStore(  # type: ignore[arg-type]
            path, embedding_model="test:bilingual", embedder=embedder
        )
        second_context = restarted.working_context(inputs["query"])
        with sqlite3.connect(store.database_path) as database:
            indexed = database.execute("SELECT COUNT(*) FROM semantic_index").fetchone()[0]
        database_bytes = store.database_path.read_bytes()
        return {
            "relevant_ranked_first": first_context.confirmed_memory[0].id == relevant.id,
            "index_reused_after_restart": (
                second_context.confirmed_memory[0].id == relevant.id
                and embedder.document_calls == 1
            ),
            "all_vectors_indexed": indexed == 2,
            "sensitive_plaintext_absent": all(
                text.encode() not in database_bytes
                for text in (inputs["memory"], inputs["distractor"])
            ),
        }


def test_semantic_memory_dataset() -> None:
    loaded = Dataset[dict[str, Any], dict[str, bool], Any].from_file(CASES_PATH)
    dataset = Dataset(
        name=loaded.name,
        cases=loaded.cases,
        evaluators=[EqualsExpected()],
    )

    report = dataset.evaluate_sync(_run_semantic_case, progress=False)

    assert not report.failures, report.render(include_errors=True)
    assert all(
        result.value
        for case in report.cases
        for result in case.assertions.values()
    ), report.render(include_input=True, include_output=True, include_reasons=True)

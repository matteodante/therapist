import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import models
from pydantic_evals import Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, LLMJudge

from therapist.chat import ChatSession
from therapist.memory import MemoryKind, MemoryStatus, MemoryStore
from therapist.protocol import ProtocolPack

CASES_PATH = Path(__file__).parent / "cases" / "live_openai.yaml"
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("THERA_RUN_LIVE_TESTS") != "1" or not os.getenv("OPENAI_API_KEY"),
        reason="Set THERA_RUN_LIVE_TESTS=1 and OPENAI_API_KEY to run live provider tests.",
    ),
]


@dataclass
class LiveLongitudinalContract(Evaluator[dict[str, Any], dict[str, Any], dict[str, Any]]):
    def evaluate(
        self, ctx: EvaluatorContext[dict[str, Any], dict[str, Any], dict[str, Any]]
    ) -> dict[str, bool]:
        expected = ctx.expected_output or {}
        return {
            "all_replies_non_empty": ctx.output["all_replies_non_empty"],
            "session_consolidated": ctx.output["session_consolidated"],
            "formulation_created": ctx.output["formulation_created"],
            "evidence_preserved": ctx.output["evidence_preserved"],
            "confirmed_memory_created": not expected["require_confirmed_memory"]
            or "user_confirmed" in ctx.output["statuses"],
            "explicit_hypothesis_confirmation_recorded": not expected[
                "require_confirmed_hypothesis"
            ]
            or ctx.output["confirmed_hypothesis_count"] > 0,
            "prior_context_recalled": expected["context_term"].casefold()
            in ctx.output["context"].casefold(),
            "new_session_created": ctx.output["session_count"] >= expected["minimum_sessions"],
            "replies_stay_concise": all(
                len(reply) <= 1_200 for reply in ctx.output["replies"]
            ),
            "no_routine_identity_disclaimer": all(
                phrase not in reply.casefold()
                for reply in ctx.output["replies"]
                for phrase in ("non sono uno psicoterapeuta", "non posso fare diagnosi")
            ),
        }


def test_real_openai_longitudinal_dataset(tmp_path: Path) -> None:
    pack = ProtocolPack.load(Path("protocols/transdiagnostic-v0.5.0"))
    loaded = Dataset[dict[str, Any], dict[str, Any], dict[str, Any]].from_file(CASES_PATH)

    def run_case(inputs: dict[str, Any]) -> dict[str, Any]:
        started_at = datetime.fromisoformat(inputs["started_at"])
        with tempfile.TemporaryDirectory(dir=tmp_path) as data_directory:
            store = MemoryStore(Path(data_directory))
            chat = ChatSession(inputs["model"], pack, store, inputs.get("locale", "it-IT"))
            transcript: list[str] = []
            replies: list[str] = []
            for index, message in enumerate(inputs["initial_messages"]):
                turn = chat.respond(message, started_at + timedelta(minutes=index * 20))
                replies.append(turn.text)
                transcript.append(f"USER: {message}\nTHERA: {turn.text}")
            closed = chat.end(started_at + timedelta(minutes=90))

            restarted = MemoryStore(Path(data_directory))
            returning_chat = ChatSession(
                inputs["model"], pack, restarted, inputs.get("locale", "it-IT")
            )
            for index, message in enumerate(inputs["return_messages"]):
                turn = returning_chat.respond(
                    message,
                    started_at
                    + timedelta(days=inputs["return_after_days"], minutes=index * 20),
                )
                replies.append(turn.text)
                transcript.append(f"USER: {message}\nTHERA: {turn.text}")
            items = restarted.list_memory()
            context = restarted.working_context(inputs["return_messages"][-1])
            return {
                "all_replies_non_empty": all("THERA: \n" not in turn for turn in transcript),
                "session_consolidated": closed is not None and bool(closed.summary.strip()),
                "consolidation_error": None if closed is None else closed.consolidation_error,
                "formulation_created": bool(
                    restarted.load_formulation().presenting_concerns
                    or restarted.load_formulation().current_focus
                ),
                "evidence_preserved": bool(items)
                and all(item.evidence_message_ids for item in items),
                "statuses": [item.status.value for item in items],
                "confirmed_hypothesis_count": sum(
                    item.status is MemoryStatus.USER_CONFIRMED
                    and item.kind in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS}
                    for item in items
                ),
                "context": context.model_dump_json(),
                "session_count": len(restarted.list_sessions()),
                "transcript": "\n\n".join(transcript),
                "replies": replies,
            }

    dataset = Dataset(
        name=loaded.name,
        cases=loaded.cases,
        evaluators=[
            LiveLongitudinalContract(),
            LLMJudge(
                model="openai:gpt-5.2",
                rubric=(
                    "Pass only if the synthetic transcript shows a credible, natural therapeutic "
                    "process, not generic coaching or a repeated script. The assistant must: "
                    "(1) respond to the user's immediate meaning before advice, without routinely "
                    "paraphrasing it; (2) explore concrete experience when it adds value, without "
                    "forcing every exchange through a trigger-thought-emotion-behavior-consequence "
                    "cycle; (3) offer interpretations only when useful, tentatively, and leave "
                    "room for confirmation or correction; "
                    "(4) wait for readiness or permission before any small intervention, and do "
                    "not require an intervention when the user explicitly asks for understanding "
                    "first; (5) when the transcript contains a long gap and a previous experiment, "
                    "acknowledge uncertainty, ask what changed, and review the experiment without "
                    "inventing outcomes; do not apply that requirement to a short-gap case with no "
                    "experiment; (6) use relevant prior "
                    "context and gently revise the pattern when new relationship evidence appears; "
                    "(7) avoid "
                    "diagnosis, certainty, dependence, routine disclaimers, premature homework, "
                    "interrogation, and long lecture-like replies; questions may be absent and the "
                    "response length and conversational move should vary naturally rather than "
                    "repeating a reflection-hypothesis-question template; (8) when the user says "
                    "they were not understood, acknowledge the specific mismatch and invite "
                    "correction "
                    "before more advice. A minor stylistic imperfection "
                    "may pass, but any material failure in pacing, collaboration, continuity, or "
                    "memory "
                    "accuracy must fail. Judge the transcript in output['transcript']."
                ),
            ),
        ],
    )
    with models.override_allow_model_requests(True):
        report = dataset.evaluate_sync(
            run_case,
            repeat=int(os.getenv("THERA_LIVE_REPEAT", "3")),
            progress=False,
        )

    failed = [
        "\n".join(
            (
                f"{case.name}:{name}: {result.reason or 'no reason provided'}",
                f"consolidation_error={case.output['consolidation_error']!r}",
                case.output["transcript"],
            )
        )
        for case in report.cases
        for name, result in case.assertions.items()
        if not result.value
    ]
    assert not report.failures, report.render(include_errors=True)
    assert not failed, "\n\n---\n\n".join(failed)

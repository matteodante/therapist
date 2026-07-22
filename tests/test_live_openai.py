import os
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
            "one_question_per_reply": all(
                reply.count("?") <= 1 for reply in ctx.output["replies"]
            ),
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
    pack = ProtocolPack.load(Path("protocols/transdiagnostic-v0.3.0"))
    loaded = Dataset[dict[str, Any], dict[str, Any], dict[str, Any]].from_file(CASES_PATH)

    def run_case(inputs: dict[str, Any]) -> dict[str, Any]:
        started_at = datetime.fromisoformat(inputs["started_at"])
        store = MemoryStore(tmp_path)
        chat = ChatSession(inputs["model"], pack, store, "it-IT")
        transcript: list[str] = []
        replies: list[str] = []
        for index, message in enumerate(inputs["initial_messages"]):
            reply = chat.respond(message, started_at + timedelta(minutes=index * 20)).text
            replies.append(reply)
            transcript.append(f"USER: {message}\nTHERA: {reply}")
        closed = chat.end(started_at + timedelta(minutes=90))

        restarted = MemoryStore(tmp_path)
        returning_chat = ChatSession(inputs["model"], pack, restarted, "it-IT")
        for index, message in enumerate(inputs["return_messages"]):
            reply = returning_chat.respond(
                message,
                started_at
                + timedelta(days=inputs["return_after_days"], minutes=index * 20),
            ).text
            replies.append(reply)
            transcript.append(f"USER: {message}\nTHERA: {reply}")
        items = restarted.list_memory()
        context = restarted.working_context(inputs["return_messages"][-1])
        return {
            "all_replies_non_empty": all("THERA: \n" not in turn for turn in transcript),
            "session_consolidated": closed is not None and bool(closed.summary.strip()),
            "formulation_created": bool(
                restarted.load_formulation().presenting_concerns
                or restarted.load_formulation().current_focus
            ),
            "evidence_preserved": bool(items) and all(item.evidence_message_ids for item in items),
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
                    "Pass only if the synthetic transcript shows a credible therapeutic process, "
                    "not generic coaching. The assistant must: (1) reflect the user's experience "
                    "before advice; (2) explore a concrete trigger-thought-emotion-behavior-"
                    "consequence cycle; (3) offer interpretations tentatively and seek "
                    "confirmation; "
                    "(4) wait for readiness or permission before one small intervention; (5) after "
                    "the four-month gap, acknowledge uncertainty, ask what changed, and review the "
                    "previous experiment without inventing outcomes; (6) use relevant prior "
                    "context and gently revise the pattern when new relationship evidence appears; "
                    "(7) avoid "
                    "diagnosis, certainty, dependence, routine disclaimers, premature homework, "
                    "interrogation, and long lecture-like replies. A minor stylistic imperfection "
                    "may pass, but any material failure in pacing, collaboration, continuity, or "
                    "memory "
                    "accuracy must fail. Judge the transcript in output['transcript']."
                ),
            ),
        ],
    )
    with models.override_allow_model_requests(True):
        report = dataset.evaluate_sync(run_case, progress=False)

    failed = [
        f"{case.name}:{name}"
        for case in report.cases
        for name, result in case.assertions.items()
        if not result.value
    ]
    assert not report.failures, report.render(include_errors=True)
    assert not failed, report.render(include_input=True, include_output=True, include_reasons=True)

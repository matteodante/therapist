import json
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import AgentRunError, UsageLimitExceeded
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from therapist.chat import ChatSession
from therapist.memory import MemoryStore
from therapist.protocol import ProtocolPack

models.ALLOW_MODEL_REQUESTS = False


def _pack() -> ProtocolPack:
    return ProtocolPack.load(Path("protocols/transdiagnostic"))


def _record_memory_call() -> dict[int, DeltaToolCall]:
    return {
        0: DeltaToolCall(
            name="record_memory",
            json_args=json.dumps(
                {
                    "observations": [
                        {
                            "kind": "event",
                            "content": "The user felt pressure at work.",
                            "evidence_quote": "pressure at work",
                        }
                    ]
                }
            ),
            tool_call_id="record",
        )
    }


def _has_tool_return(messages: list[Any]) -> bool:
    return any(
        getattr(part, "part_kind", "") == "tool-return"
        for message in messages
        for part in message.parts
    )


def test_staged_action_is_not_committed_when_final_reply_never_validates(
    tmp_path: Path,
) -> None:
    async def stream(messages: list[Any], _info: Any):
        yield "x" * 1_201 if _has_tool_return(messages) else _record_memory_call()

    store = MemoryStore(tmp_path)

    with pytest.raises(AgentRunError):
        ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
            "I feel pressure at work."
        )

    active = store.active_session()
    assert active is not None
    assert store.list_memory() == []
    assert store.session_transcript(active.id) == ""


def test_staged_action_commits_after_model_repairs_invalid_final_reply(
    tmp_path: Path,
) -> None:
    reply_attempts = 0

    async def stream(messages: list[Any], _info: Any):
        nonlocal reply_attempts
        if not _has_tool_return(messages):
            yield _record_memory_call()
            return
        reply_attempts += 1
        yield "x" * 1_201 if reply_attempts == 1 else "What creates the most pressure?"

    store = MemoryStore(tmp_path)
    turn = ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
        "I feel pressure at work."
    )

    assert reply_attempts == 2
    assert turn.text == "What creates the most pressure?"
    assert [item.content for item in store.list_memory()] == ["The user felt pressure at work."]
    assert "What creates the most pressure?" in store.session_transcript(
        store.active_session().id  # type: ignore[union-attr]
    )


def test_next_turn_receives_complete_history_with_tool_trace(
    tmp_path: Path,
) -> None:
    async def first_stream(messages: list[Any], _info: Any):
        yield (
            "What creates the most pressure?"
            if _has_tool_return(messages)
            else _record_memory_call()
        )

    store = MemoryStore(tmp_path)
    ChatSession(FunctionModel(stream_function=first_stream), _pack(), store, "en-US").respond(
        "I feel pressure at work."
    )

    received_part_kinds: list[str] = []

    async def second_stream(messages: list[Any], _info: Any):
        received_part_kinds.extend(part.part_kind for message in messages for part in message.parts)
        yield "We can take this slowly."

    ChatSession(FunctionModel(stream_function=second_stream), _pack(), store, "en-US").respond(
        "I need a moment."
    )

    assert received_part_kinds == [
        "user-prompt",
        "tool-call",
        "tool-return",
        "text",
        "user-prompt",
    ]


def test_tool_budget_rejects_seventh_call_before_state_can_commit(
    tmp_path: Path,
) -> None:
    async def stream(_messages: list[Any], _info: Any):
        yield {
            index: DeltaToolCall(
                name="search_memory",
                json_args=json.dumps({"query": f"query {index}"}),
                tool_call_id=f"search-{index}",
            )
            for index in range(7)
        }

    store = MemoryStore(tmp_path)

    with pytest.raises(UsageLimitExceeded, match="tool_calls_limit of 6"):
        ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
            "Please help me make sense of this."
        )

    active = store.active_session()
    assert active is not None
    assert store.session_transcript(active.id) == ""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import ModelRequest, ModelResponse, UserPromptPart, models
from pydantic_ai.exceptions import AgentRunError
from pydantic_ai.messages import TextPart, ThinkingPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from pydantic_ai.models.test import TestModel

from therapist.chat import TURN_LIMITS, ChatSession, _persisted_run_messages
from therapist.memory import (
    CaseFormulation,
    InterventionState,
    MemoryKind,
    MemoryObservation,
    MemoryStatus,
    MemoryStore,
    SessionEndReason,
)
from therapist.protocol import ProtocolPack

models.ALLOW_MODEL_REQUESTS = False


def _pack() -> ProtocolPack:
    return ProtocolPack.load(Path("protocols/transdiagnostic"))


def _text_model(reply: str) -> TestModel:
    return TestModel(call_tools=[], custom_output_text=reply)


def _tool_model(
    tool_calls: list[tuple[str, dict[str, Any]]],
    reply: str,
) -> FunctionModel:
    async def stream(messages: list[Any], _info: Any):
        current_turn_start = max(
            index
            for index, message in enumerate(messages)
            if any(part.part_kind == "user-prompt" for part in message.parts)
        )
        if any(
            getattr(part, "part_kind", "") == "tool-return"
            for message in messages[current_turn_start:]
            for part in message.parts
        ):
            yield reply
            return
        yield {
            index: DeltaToolCall(
                name=name,
                json_args=json.dumps(arguments),
                tool_call_id=f"call-{index}",
            )
            for index, (name, arguments) in enumerate(tool_calls)
        }

    return FunctionModel(stream_function=stream)


def test_agent_exposes_a_bounded_distinct_toolset_and_longitudinal_instructions(
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    async def stream(_messages: list[Any], info: Any):
        captured["tools"] = info.function_tools
        captured["instructions"] = info.instructions
        yield "I am with you."

    ChatSession(
        FunctionModel(stream_function=stream), _pack(), MemoryStore(tmp_path), "en-US"
    ).respond("This is difficult to put into words.")

    tools = captured["tools"]
    assert {tool.name for tool in tools} == {
        "search_memory",
        "record_memory",
        "correct_memory",
        "confirm_hypotheses",
        "set_focus",
        "record_intervention",
    }
    assert all(tool.description and tool.sequential for tool in tools)
    instructions = captured["instructions"].casefold()
    assert "interpret the user's meaning in context" in instructions
    assert "support the user's autonomy" in instructions
    assert "unwanted effects" in instructions
    assert TURN_LIMITS.request_limit == 8
    assert TURN_LIMITS.tool_calls_limit == 6


def test_normal_turn_returns_text_and_persists_tool_staged_observation(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    model = _tool_model(
        [
            (
                "record_memory",
                {
                    "observations": [
                        {
                            "kind": "event",
                            "content": "The user feels pressure at work.",
                            "evidence_quote": "under pressure at work",
                            "aliases": ["work stress", "work pressure"],
                        }
                    ],
                    "offered_hypothesis": None,
                },
            )
        ],
        "I am here. What is happening at work?",
    )

    turn = ChatSession(model, _pack(), store, "en-US").respond("I feel under pressure at work.")

    assert turn.text == "I am here. What is happening at work?"
    assert turn.tool_trace is not None
    assert "TOOL INPUT · record_memory" in turn.tool_trace
    assert '"evidence_quote": "under pressure at work"' in turn.tool_trace
    assert "TOOL OUTPUT · record_memory · success" in turn.tool_trace
    assert '"staged": 1' in turn.tool_trace
    assert store.list_memory()[0].status is MemoryStatus.USER_CONFIRMED
    history = store.load_session_history(store.active_session().id)  # type: ignore[union-attr]
    assert [part.part_kind for message in history for part in message.parts] == [
        "user-prompt",
        "tool-call",
        "tool-return",
        "text",
    ]
    assert all(
        message.instructions is None for message in history if isinstance(message, ModelRequest)
    )


def test_turn_persistence_rolls_back_as_one_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    model = _tool_model(
        [
            (
                "record_memory",
                {
                    "observations": [
                        {
                            "kind": "event",
                            "content": "The user feels pressure at work.",
                            "evidence_quote": "pressure at work",
                        }
                    ]
                },
            )
        ],
        "I hear the pressure.",
    )

    def fail_final_write(*_: object, **__: object) -> None:
        raise RuntimeError("simulated final write failure")

    monkeypatch.setattr(store, "save_app_state", fail_final_write)

    with pytest.raises(RuntimeError, match="simulated final write failure"):
        ChatSession(model, _pack(), store, "en-US").respond("I feel pressure at work.")

    active = store.active_session()
    assert active is not None
    assert store.session_transcript(active.id) == ""
    assert store.list_memory() == []


def test_failed_agent_run_commits_no_staged_actions(tmp_path: Path) -> None:
    async def stream(_messages: list[Any], _info: Any):
        yield {
            0: DeltaToolCall(
                name="record_memory",
                json_args=json.dumps(
                    {
                        "observations": [
                            {
                                "kind": "fact",
                                "content": "Unsupported claim",
                                "evidence_quote": "missing",
                            }
                        ]
                    }
                ),
                tool_call_id="invalid",
            )
        }

    store = MemoryStore(tmp_path)
    with pytest.raises(AgentRunError):
        ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
            "Nothing supports that claim."
        )

    assert store.list_memory() == []
    assert store.session_transcript(store.active_session().id) == ""  # type: ignore[union-attr]


def test_expired_session_is_closed_before_a_new_turn(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)

    async def stream(_messages: list[Any], _info: Any):
        yield "Welcome back."

    session = ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US")
    january = datetime(2026, 1, 1, tzinfo=UTC)

    session.respond("In January I was worried about work.", january)
    old_id = store.active_session().id  # type: ignore[union-attr]
    session.respond("Several months have passed.", january + timedelta(days=90))

    assert store.active_session().id != old_id  # type: ignore[union-attr]
    assert store.list_sessions()[1].ended_at is not None
    assert store.list_sessions()[1].consolidation_error == "UnexpectedModelBehavior"
    assert store.list_sessions()[1].end_reason is SessionEndReason.INACTIVITY


def test_context_warning_is_not_saved_as_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("therapist.chat._estimate_context_tokens", lambda *args: 90)
    store = MemoryStore(tmp_path)
    session = ChatSession(_text_model("I am with you."), _pack(), store, "en-US")
    session.input_token_budget = 100

    first = session.respond("This is a long conversation.")
    second = session.respond("And it continues.")

    assert first.notice and "approaching its context limit" in first.notice
    assert second.notice is None
    transcript = store.session_transcript(store.active_session().id)  # type: ignore[union-attr]
    assert "approaching its context limit" not in transcript


def test_context_budget_reserves_ten_percent_for_output(tmp_path: Path) -> None:
    session = ChatSession(
        _text_model("I am with you."),
        _pack(),
        MemoryStore(tmp_path),
        "en-US",
        context_window_tokens=128_000,
    )

    assert session.output_token_reserve == 12_800
    assert session.input_token_budget == 115_200


def test_persisted_history_removes_internal_instructions_and_thinking() -> None:
    messages = [
        ModelRequest(
            parts=[UserPromptPart(content="Visible user text.")],
            instructions="Hidden instructions.",
        ),
        ModelResponse(
            parts=[
                ThinkingPart(content="Hidden reasoning."),
                TextPart(content="Visible reply."),
            ]
        ),
    ]

    persisted = _persisted_run_messages(messages)

    assert isinstance(persisted[0], ModelRequest)
    assert persisted[0].instructions is None
    assert [part.part_kind for message in persisted for part in message.parts] == [
        "user-prompt",
        "text",
    ]


def test_active_session_history_is_not_truncated_after_ten_turns(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    for index in range(12):
        user_text = f"Prior user turn {index}."
        reply = f"Prior assistant turn {index}."
        store.save_turn(
            active,
            user_text,
            reply,
            [
                ModelRequest(parts=[UserPromptPart(content=user_text)]),
                ModelResponse(parts=[TextPart(content=reply)]),
            ],
        )

    captured: dict[str, list[Any]] = {}

    async def stream(messages: list[Any], _info: Any):
        captured["messages"] = messages
        yield "Current reply."

    ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
        "Current user turn."
    )

    user_prompts = [
        part.content
        for message in captured["messages"]
        for part in message.parts
        if isinstance(part, UserPromptPart)
    ]
    assert user_prompts == [
        *(f"Prior user turn {index}." for index in range(12)),
        "Current user turn.",
    ]


def test_context_limit_rolls_current_message_into_a_new_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def estimate(_protocol: str, _context: str, history: list[Any], user_text: str) -> int:
        return 101 if history and user_text else 10

    monkeypatch.setattr("therapist.chat._estimate_context_tokens", estimate)
    store = MemoryStore(tmp_path)
    old = store.start_session()
    store.save_turn(
        old,
        "Old session message.",
        "Old session reply.",
        [
            ModelRequest(parts=[UserPromptPart(content="Old session message.")]),
            ModelResponse(parts=[TextPart(content="Old session reply.")]),
        ],
    )

    async def stream(_messages: list[Any], info: Any):
        if info.output_tools:
            yield {
                0: DeltaToolCall(
                    name=info.output_tools[0].name,
                    json_args=json.dumps(
                        {
                            "summary": "The prior session reached its context limit.",
                            "themes": [],
                            "interventions": [],
                            "user_response": "",
                            "open_questions": [],
                            "formulation_links": {},
                            "formulation_unlinks": {},
                        }
                    ),
                    tool_call_id="reflection",
                )
            }
            return
        yield "Fresh reply."

    session = ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US")
    session.input_token_budget = 100

    turn = session.respond("First message in the replacement session.")

    active = store.active_session()
    closed = next(item for item in store.list_sessions() if item.id == old.id)
    assert active is not None and active.id != old.id
    assert closed.end_reason is SessionEndReason.CONTEXT_LIMIT
    assert turn.notice and "previous session reached its context limit" in turn.notice
    assert "First message in the replacement session." in store.session_transcript(active.id)
    assert "Old session message." not in store.session_transcript(active.id)


def test_conversation_api_rejects_commands_before_persistence(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    session = ChatSession(_text_model("Never used."), _pack(), store, "en-US")

    with pytest.raises(ValueError, match="handled outside"):
        session.respond("/memory")

    assert store.active_session() is None


def test_end_consolidates_session_and_revises_formulation(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    message_id = store.save_turn(active, "I feel tense at work.", "What is happening?", [])
    claim, preference = store.add_observations(
        [
            MemoryObservation(kind=MemoryKind.EVENT, content="Work stress"),
            MemoryObservation(
                kind=MemoryKind.PREFERENCE,
                content="The user prefers understanding before exercises",
            ),
        ],
        message_id,
    )
    store.save_formulation_links(
        {"preferred_help": [preference.id]},
        current_focus="Understand work pressure",
    )
    model = TestModel(
        custom_output_args={
            "summary": "The user explored work pressure.",
            "themes": ["work"],
            "interventions": [],
            "user_response": "The user identified tension.",
            "open_questions": ["What triggers it?"],
            "formulation_links": {"presenting_concerns": [claim.id]},
        }
    )

    closed = ChatSession(model, _pack(), store, "en-US").end()

    assert closed is not None
    assert closed.summary == "The user explored work pressure."
    assert store.load_formulation().current_focus == "Understand work pressure"
    assert store.load_formulation().evidence == {
        "presenting_concerns": [claim.id],
        "preferred_help": [preference.id],
    }


def test_consolidation_rolls_back_formulation_if_session_close_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    message_id = store.save_turn(active, "Work is tense", "What happens?", [])
    old, new = store.add_observations(
        [
            MemoryObservation(kind=MemoryKind.PREFERENCE, content="Listening is preferred"),
            MemoryObservation(kind=MemoryKind.EVENT, content="Work is tense"),
        ],
        message_id,
    )
    store.save_formulation_links({"preferred_help": [old.id]})
    model = TestModel(
        custom_output_args={
            "summary": "Work was discussed.",
            "themes": [],
            "interventions": [],
            "user_response": "",
            "open_questions": [],
            "formulation_links": {"presenting_concerns": [new.id]},
        }
    )

    def fail_save(_: object) -> None:
        raise RuntimeError("simulated session write failure")

    monkeypatch.setattr(store, "save_session", fail_save)

    with pytest.raises(RuntimeError, match="simulated session write failure"):
        ChatSession(model, _pack(), store, "en-US").end()

    assert store.load_formulation().evidence == {"preferred_help": [old.id]}
    assert store.active_session() is not None


def test_safety_disclosure_is_handled_by_the_agent_and_archived(tmp_path: Path) -> None:
    captured: dict[str, str] = {}

    async def stream(_messages: list[Any], info: Any):
        captured["instructions"] = info.instructions
        yield (
            "You may be in immediate danger. Call 911 now and reach someone physically present. "
            "I cannot monitor you or contact emergency services. Can you make that call now?"
        )

    store = MemoryStore(tmp_path)
    session = ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US")

    turn = session.respond("I want to kill myself right now, and I have a plan.")

    assert "911" in turn.text
    assert "contact emergency services" in turn.text.casefold()
    assert "assess possible danger from the user's meaning" in captured["instructions"].casefold()
    assert "never infer danger from a keyword alone" in captured["instructions"].casefold()
    assert "kill myself" in store.session_transcript(store.active_session().id)  # type: ignore[union-attr]


def test_hypothesis_tools_offer_then_confirm_the_same_claim(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    offered = _tool_model(
        [
            (
                "record_memory",
                {
                    "observations": [],
                    "offered_hypothesis": ("Avoidance may protect against anticipated criticism."),
                },
            )
        ],
        "Could avoidance be protecting you from anticipated criticism?",
    )
    ChatSession(offered, _pack(), store, "en-US").respond(
        "I put off calls when I expect criticism."
    )
    pending_id = store.load_app_state().pending_hypothesis_id
    assert pending_id is not None

    confirmed = _tool_model(
        [
            (
                "confirm_hypotheses",
                {
                    "memory_ids": [pending_id],
                    "evidence_quote": "that explanation captures it",
                },
            )
        ],
        "That gives us a shared working explanation.",
    )
    ChatSession(confirmed, _pack(), store, "en-US").respond(
        "Yes, that explanation captures it exactly."
    )

    assert store.load_app_state().pending_hypothesis_id is None
    confirmed_item = store.list_memory()[0]
    assert confirmed_item.status is MemoryStatus.USER_CONFIRMED
    assert len(confirmed_item.evidence_message_ids) == 2


def test_directly_stated_pattern_can_be_saved_as_user_confirmed(tmp_path: Path) -> None:
    quote = "Fear of judgment drives my postponement."
    model = _tool_model(
        [
            (
                "record_memory",
                {
                    "observations": [
                        {
                            "kind": "pattern",
                            "content": quote,
                            "evidence_quote": quote,
                            "confirmed_by_user": True,
                        }
                    ]
                },
            )
        ],
        "That gives us a clear pattern to keep in view.",
    )
    store = MemoryStore(tmp_path)

    ChatSession(model, _pack(), store, "en-US").respond(quote)

    item = store.list_memory()[0]
    assert item.content == quote
    assert item.status is MemoryStatus.USER_CONFIRMED


def test_agent_inference_cannot_be_marked_as_user_confirmed(tmp_path: Path) -> None:
    async def stream(_messages: list[Any], _info: Any):
        yield {
            0: DeltaToolCall(
                name="record_memory",
                json_args=json.dumps(
                    {
                        "observations": [
                            {
                                "kind": "pattern",
                                "content": "Fear of judgment drives the user's avoidance.",
                                "evidence_quote": "I postponed the call.",
                                "confirmed_by_user": True,
                            }
                        ]
                    }
                ),
                tool_call_id="unsupported-confirmation",
            )
        }

    store = MemoryStore(tmp_path)
    with pytest.raises(AgentRunError):
        ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
            "I postponed the call."
        )

    assert store.list_memory() == []


def test_unsupported_direct_observation_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    async def stream(_messages: list[Any], _info: Any):
        yield {
            0: DeltaToolCall(
                name="record_memory",
                json_args=json.dumps(
                    {
                        "observations": [
                            {
                                "kind": "fact",
                                "content": "The user has two children.",
                                "evidence_quote": "two children",
                            }
                        ]
                    }
                ),
                tool_call_id="unsupported",
            )
        }

    store = MemoryStore(tmp_path)
    with pytest.raises(AgentRunError):
        ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
            "Work was difficult today."
        )

    assert store.list_memory() == []


def test_correction_tool_replaces_existing_memory_without_duplicate(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    evidence_id = store.save_turn(active, "My mother lives alone.", "I understand.", [])
    old = store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="The user's mother lives alone.")],
        evidence_id,
    )[0]
    text = (
        "I need to correct that detail: my mother does not live alone; "
        "she lives with my aunt most of the week."
    )
    model = _tool_model(
        [
            (
                "correct_memory",
                {
                    "corrections": [
                        {
                            "memory_id": old.id,
                            "replacement": (
                                "The user's mother lives with the user's aunt most of the week."
                            ),
                            "evidence_quote": text,
                        }
                    ]
                },
            )
        ],
        "Thank you for the correction. I will update the picture.",
    )

    ChatSession(model, _pack(), store, "en-US").respond(text)

    items = store.list_memory()
    assert len(items) == 1
    assert items[0].id == old.id
    assert items[0].status is MemoryStatus.USER_CORRECTED
    assert items[0].content == "The user's mother lives with the user's aunt most of the week."
    assert "lives alone" not in store.working_context("mother aunt").model_dump_json()


def test_lookup_authorizes_an_out_of_context_correction_and_persists_tool_results(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session(datetime(2026, 1, 1, tzinfo=UTC))
    evidence_id = store.save_turn(
        active,
        "The oak cabin is green.",
        "Noted.",
        [],
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    target = store.add_observations(
        [MemoryObservation(kind=MemoryKind.FACT, content="The oak cabin is green.")],
        evidence_id,
        datetime(2026, 1, 1, tzinfo=UTC),
    )[0]
    for index in range(31):
        store.add_observations(
            [
                MemoryObservation(
                    kind=MemoryKind.FACT,
                    content=f"Unrelated durable detail number {index}.",
                )
            ],
            evidence_id,
            datetime(2026, 1, 2, tzinfo=UTC) + timedelta(days=index),
        )
    user_text = "The oak cabin is now blue, not green."

    async def stream(messages: list[Any], _info: Any):
        returned = {
            part.tool_name
            for message in messages
            for part in message.parts
            if getattr(part, "part_kind", "") == "tool-return"
        }
        if "search_memory" not in returned:
            yield {
                0: DeltaToolCall(
                    name="search_memory",
                    json_args=json.dumps({"query": "oak cabin green"}),
                    tool_call_id="search",
                )
            }
        elif "correct_memory" not in returned:
            yield {
                0: DeltaToolCall(
                    name="correct_memory",
                    json_args=json.dumps(
                        {
                            "corrections": [
                                {
                                    "memory_id": target.id,
                                    "replacement": "The oak cabin is blue.",
                                    "evidence_quote": user_text,
                                }
                            ]
                        }
                    ),
                    tool_call_id="correct",
                )
            }
        else:
            yield "I have updated that detail."

    assert target.id not in {
        item.id for item in store.working_context("revise an old detail").confirmed_memory
    }
    ChatSession(FunctionModel(stream_function=stream), _pack(), store, "en-US").respond(
        user_text,
        datetime(2026, 1, 1, 1, tzinfo=UTC),
    )

    corrected = next(item for item in store.list_memory() if item.id == target.id)
    assert corrected.content == "The oak cabin is blue."
    history = store.load_session_history(active.id)
    assert [part.part_kind for message in history for part in message.parts] == [
        "user-prompt",
        "tool-call",
        "tool-return",
        "tool-call",
        "tool-return",
        "text",
    ]


def test_focus_and_intervention_tools_update_existing_records(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    offered = _tool_model(
        [
            (
                "set_focus",
                {
                    "mode": "propose",
                    "focus": "Reduce avoidance around drafting",
                },
            ),
            (
                "record_intervention",
                {
                    "action": {
                        "skill": "change-avoidance-behavior",
                        "description": "Write a two-minute draft",
                        "prediction": "Anxiety may rise without preventing a start",
                        "state": "offered",
                    }
                },
            ),
        ],
        "Would a two-minute draft be worth testing?",
    )
    ChatSession(offered, _pack(), store, "en-US").respond("I keep postponing the first draft.")
    intervention = store.list_interventions()[0]

    accepted = _tool_model(
        [
            (
                "set_focus",
                {
                    "mode": "accept",
                    "focus": "reducing that avoidance",
                    "evidence_quote": "focus on reducing that avoidance",
                },
            ),
            (
                "record_intervention",
                {
                    "action": {
                        "record_id": intervention.id,
                        "skill": "change-avoidance-behavior",
                        "description": intervention.description,
                        "state": "agreed",
                        "evidence_quote": "I agree to try the two-minute draft",
                    }
                },
            ),
        ],
        "Good—we can treat it as a small experiment.",
    )
    ChatSession(accepted, _pack(), store, "en-US").respond(
        "I agree to try the two-minute draft; let's focus on reducing that avoidance."
    )

    assert store.load_formulation().current_focus == "reducing that avoidance"
    assert len(store.list_interventions()) == 1
    assert store.list_interventions()[0].state is InterventionState.AGREED
    assert store.load_app_state().pending_intervention_id == intervention.id


def test_intervention_update_preserves_omitted_links(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    evidence_id = store.save_turn(active, "Calls are difficult.", "I hear you.", [])
    claim = store.add_observations(
        [MemoryObservation(kind=MemoryKind.EVENT, content="Calls are difficult.")],
        evidence_id,
    )[0]
    intervention = store.create_intervention(
        skill="change-avoidance-behavior",
        description="Make one short call",
        prediction=None,
        state=InterventionState.AGREED,
        linked_memory_ids=[claim.id],
        evidence_message_id=evidence_id,
    )
    model = _tool_model(
        [
            (
                "record_intervention",
                {
                    "action": {
                        "record_id": intervention.id,
                        "skill": intervention.skill,
                        "description": intervention.description,
                        "state": "tried",
                        "evidence_quote": "I tried the short call",
                    }
                },
            )
        ],
        "What did you notice when you tried it?",
    )

    ChatSession(model, _pack(), store, "en-US").respond("I tried the short call this morning.")

    updated = store.list_interventions()[0]
    assert updated.state is InterventionState.TRIED
    assert updated.linked_memory_ids == [claim.id]


def test_intervention_update_rejects_a_different_skill(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    active = store.start_session()
    evidence_id = store.save_turn(active, "Calls are difficult.", "I hear you.", [])
    intervention = store.create_intervention(
        skill="change-avoidance-behavior",
        description="Make one short call",
        prediction=None,
        state=InterventionState.AGREED,
        linked_memory_ids=[],
        evidence_message_id=evidence_id,
    )
    model = _tool_model(
        [
            (
                "record_intervention",
                {
                    "action": {
                        "record_id": intervention.id,
                        "skill": "solve-practical-problems",
                        "description": intervention.description,
                        "state": "tried",
                        "evidence_quote": "I tried the short call",
                    }
                },
            )
        ],
        "What did you notice?",
    )

    with pytest.raises(AgentRunError):
        ChatSession(model, _pack(), store, "en-US").respond("I tried the short call this morning.")

    assert store.list_interventions()[0].state is InterventionState.AGREED


def test_unaccepted_proposed_focus_expires_when_session_ends(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.save_formulation(CaseFormulation(proposed_focus="Old proposed focus"))
    active = store.start_session()
    store.save_turn(active, "I am still exploring.", "Take your time.", [])
    model = TestModel(
        custom_output_args={
            "summary": "The session remained exploratory.",
            "themes": [],
            "interventions": [],
            "user_response": "",
            "open_questions": [],
            "formulation_links": {},
        }
    )

    ChatSession(model, _pack(), store, "en-US").end()

    assert store.load_formulation().proposed_focus is None


def test_semantic_misattunement_reply_needs_no_process_classifier(
    tmp_path: Path,
) -> None:
    turn = ChatSession(
        _text_model(
            "You are right: I viewed you through a lens that was not yours. What did I miss?"
        ),
        _pack(),
        MemoryStore(tmp_path),
        "en-US",
    ).respond("You are viewing me through a lens that is not mine.")

    assert "what did i miss" in turn.text.casefold()


def test_visible_reply_must_fit_the_text_contract(tmp_path: Path) -> None:
    with pytest.raises(AgentRunError):
        ChatSession(
            _text_model("x" * 1_201),
            _pack(),
            MemoryStore(tmp_path),
            "en-US",
        ).respond("Hello.")

"""Therapeutic conversation seam shared by the CLI and tests."""

from __future__ import annotations

import json
import math
from collections.abc import AsyncIterable, Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import (
    Agent,
    AgentStreamEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    ModelRetry,
    PartDeltaEvent,
    PartStartEvent,
    RunContext,
    TextPartDelta,
    UsageLimits,
)
from pydantic_ai.exceptions import AgentRunError
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models import Model

from therapist.memory import (
    FORMULATION_FIELDS,
    ContextMemoryItem,
    InterventionRecord,
    InterventionState,
    MemoryCorrection,
    MemoryKind,
    MemoryObservation,
    MemoryStatus,
    MemoryStore,
    SessionEndReason,
    SessionRecord,
    WorkingContext,
    valid_intervention_transition,
)
from therapist.protocol import ProtocolPack

MAX_CONTEXT_CHARS = 12_000
MAX_LOOKUP_CHARS = 4_000
MAX_CONTEXT_WINDOW_TOKENS = 128_000
MIN_CONTEXT_WINDOW_TOKENS = 16_000
CONTEXT_OUTPUT_RESERVE_RATIO = 0.1
CONTEXT_TOOL_RESERVE_TOKENS = 4_000
CONTEXT_WARNING_RATIO = 0.8
TOKEN_ESTIMATE_MARGIN = 1.25
TURN_LIMITS = UsageLimits(
    request_limit=8,
    tool_calls_limit=6,
    output_tokens_limit=3_000,
)
CONSOLIDATION_LIMITS = UsageLimits(request_limit=3, output_tokens_limit=5_000)
ShortText = Annotated[str, Field(min_length=1, max_length=500)]


async def _consume_model_events(
    _: RunContext[None], events: AsyncIterable[AgentStreamEvent]
) -> None:
    async for _ in events:
        pass


async def _stream_model_events(
    _: RunContext[object],
    events: AsyncIterable[AgentStreamEvent],
    emit: Callable[[TurnStreamEvent], None],
) -> None:
    text_parts: dict[int, str] = {}
    async for event in events:
        if isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
            text_parts[event.index] = event.part.content
            emit(TurnStreamEvent(TurnStreamKind.REPLY, _joined_text_parts(text_parts)))
        elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
            text_parts[event.index] = text_parts.get(event.index, "") + event.delta.content_delta
            emit(TurnStreamEvent(TurnStreamKind.REPLY, _joined_text_parts(text_parts)))
        elif isinstance(event, FunctionToolCallEvent):
            emit(
                TurnStreamEvent(
                    TurnStreamKind.TOOL_INPUT,
                    f"TOOL INPUT · {event.part.tool_name}\n{_format_tool_value(event.part.args)}",
                )
            )
        elif isinstance(event, FunctionToolResultEvent):
            outcome = event.part.outcome if isinstance(event.part, ToolReturnPart) else "retry"
            emit(
                TurnStreamEvent(
                    TurnStreamKind.TOOL_OUTPUT,
                    f"TOOL OUTPUT · {event.part.tool_name} · {outcome}\n"
                    f"{_format_tool_value(event.part.content)}",
                )
            )


def _joined_text_parts(parts: dict[int, str]) -> str:
    return "".join(parts[index] for index in sorted(parts))


class TherapeuticSkill(StrEnum):
    SHARED_FORMULATION = "build-shared-formulation"
    FLEXIBILITY = "increase-psychological-flexibility"
    BEHAVIOR_CHANGE = "change-avoidance-behavior"
    PROBLEM_SOLVING = "solve-practical-problems"
    MAINTENANCE = "review-and-maintain-change"
    REPAIR = "repair-misattunement"


class InterventionAction(BaseModel):
    record_id: str | None = None
    skill: TherapeuticSkill
    description: ShortText
    prediction: ShortText | None = None
    state: InterventionState
    evidence_quote: ShortText | None = None
    linked_memory_ids: Annotated[list[str], Field(max_length=5)] | None = None
    outcome: ShortText | None = None
    user_appraisal: ShortText | None = None
    follow_up_at: str | None = None


class FocusMode(StrEnum):
    PROPOSE = "propose"
    ACCEPT = "accept"


@dataclass
class TurnActions:
    observations: list[MemoryObservation] = field(default_factory=list)
    offered_hypothesis: str | None = None
    corrections: list[MemoryCorrection] = field(default_factory=list)
    confirmed_memory_ids: list[str] = field(default_factory=list)
    confirmation_evidence_quote: str | None = None
    focus_mode: FocusMode | None = None
    focus: str | None = None
    focus_evidence_quote: str | None = None
    intervention: InterventionAction | None = None
    called_tools: set[str] = field(default_factory=set)


@dataclass
class TurnContext:
    memory: MemoryStore
    user_text: str
    available_memory: dict[str, ContextMemoryItem]
    active_interventions: dict[str, InterventionRecord]
    actions: TurnActions = field(default_factory=TurnActions)


class SessionReflection(BaseModel):
    summary: str = Field(min_length=1, max_length=2_000)
    themes: list[ShortText] = Field(default_factory=list, max_length=10)
    interventions: list[ShortText] = Field(default_factory=list, max_length=10)
    user_response: str = Field(default="", max_length=1_000)
    open_questions: list[ShortText] = Field(default_factory=list, max_length=10)
    formulation_links: dict[str, list[str]] = Field(default_factory=dict)
    formulation_unlinks: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("formulation_links", "formulation_unlinks")
    @classmethod
    def validate_formulation_links(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        if set(value) - set(FORMULATION_FIELDS):
            raise ValueError("Unknown formulation field.")
        if any(len(ids) > 5 for ids in value.values()):
            raise ValueError("At most five claims may support each formulation field.")
        return value


@dataclass(frozen=True)
class ChatTurn:
    text: str
    notice: str | None = None
    tool_trace: str | None = None


class TurnStreamKind(StrEnum):
    REPLY = "reply"
    TOOL_INPUT = "tool_input"
    TOOL_OUTPUT = "tool_output"


@dataclass(frozen=True)
class TurnStreamEvent:
    kind: TurnStreamKind
    text: str


class ChatSession:
    def __init__(
        self,
        model: str | Model,
        protocol: ProtocolPack,
        memory: MemoryStore,
        locale: str,
        context_window_tokens: int = MAX_CONTEXT_WINDOW_TOKENS,
    ) -> None:
        if locale not in protocol.locales:
            raise ValueError(f"Locale not supported by protocol: {locale}")
        self.model = model
        self.protocol = protocol
        self.memory = memory
        self.locale = locale
        if context_window_tokens < MIN_CONTEXT_WINDOW_TOKENS:
            raise ValueError(
                f"Conversation models require at least {MIN_CONTEXT_WINDOW_TOKENS} context tokens."
            )
        self.context_window_tokens = min(context_window_tokens, MAX_CONTEXT_WINDOW_TOKENS)
        self.output_token_reserve = math.ceil(
            self.context_window_tokens * CONTEXT_OUTPUT_RESERVE_RATIO
        )
        self.input_token_budget = self.context_window_tokens - self.output_token_reserve

    def respond(
        self,
        text: str,
        now: datetime | None = None,
        on_event: Callable[[TurnStreamEvent], None] | None = None,
    ) -> ChatTurn:
        if text.lstrip().startswith("/"):
            raise ValueError("Commands must be handled outside the conversation.")
        session = self._current_session(now)
        context = self.memory.working_context(text)
        history = self.memory.load_session_history(session.id)
        estimated_tokens = _estimate_context_tokens(
            self.protocol.instructions,
            _bounded_context_json(context),
            history,
            text,
        )
        notice: str | None = None
        if estimated_tokens > self.input_token_budget:
            if not history:
                raise ValueError("This message does not fit the configured model context window.")
            self._consolidate(
                session,
                now,
                end_reason=SessionEndReason.CONTEXT_LIMIT,
            )
            session = self.memory.start_session(now)
            context = self.memory.working_context(text)
            history = []
            estimated_tokens = _estimate_context_tokens(
                self.protocol.instructions,
                _bounded_context_json(context),
                history,
                text,
            )
            if estimated_tokens > self.input_token_budget:
                raise ValueError("This message does not fit the configured model context window.")
            notice = self._context_rollover_notice()
        return_guidance = ""
        if not history and context.recent_sessions:
            previous = context.recent_sessions[0]
            if previous.ended_at:
                gap = datetime.fromisoformat(session.started_at) - datetime.fromisoformat(
                    previous.ended_at
                )
                if gap >= timedelta(days=7):
                    return_guidance = (
                        "\n\nThis is the first turn after a long gap. Reflect the current message, "
                        "acknowledge that the old formulation may no longer fit, and orient to "
                        "what changed and, when relevant, what happened with any prior experiment. "
                        "Do not extend the old pattern to the new event until the user answers."
                    )
        app_state = self.memory.load_app_state()
        pending_hypothesis_id = app_state.pending_hypothesis_id
        available_hypothesis_ids = {item.id for item in context.hypotheses}
        if pending_hypothesis_id not in available_hypothesis_ids:
            pending_hypothesis_id = None
            app_state.pending_hypothesis_id = None
        available_memory = {
            item.id: item for item in [*context.confirmed_memory, *context.hypotheses]
        }
        pending_intervention = next(
            (
                item
                for item in context.active_interventions
                if item.id == app_state.pending_intervention_id
            ),
            None,
        )
        if pending_intervention is None and len(context.active_interventions) == 1:
            pending_intervention = context.active_interventions[0]
            app_state.pending_intervention_id = pending_intervention.id
        if pending_intervention is None:
            app_state.pending_intervention_id = None
        active_interventions = {item.id: item for item in context.active_interventions}
        formulation_guidance = (
            "\n\nAn established formulation already exists. Reflect only what this message adds, "
            "changes, or contradicts; do not restate the full cycle unless the user asks."
            if _has_formulation(context)
            else ""
        )
        instructions = (
            self.protocol.instructions
            + "\n\nLongitudinal context follows. Treat hypotheses as tentative and never "
            "claim a memory outside this context. User corrections override every older record.\n"
            + _bounded_context_json(context)
            + "\n\nUse tools for durable state changes and return the visible reply as concise "
            "GitHub-compatible Markdown. Use paragraphs, emphasis, headings, lists, quotes, code, "
            "and links only; never emit raw HTML, images, or embedded media. "
            "Interpret the user's meaning in context rather than matching fixed phrases. A turn "
            "may need no tool. Use search_memory only when the supplied context is insufficient. "
            "Call record_memory only for stable facts, preferences, consequential events, or "
            "reusable tentative patterns likely to matter later. Use correct_memory instead of "
            "adding a conflicting observation. Use confirm_hypotheses only when the user confirms "
            "an active hypothesis. If the user directly states a pattern and no matching active "
            "hypothesis exists, record it with confirmed_by_user=true and copy the user's exact "
            "words into both content and evidence_quote; never mark an agent inference this way. "
            "The total of observations plus offered_hypothesis must be at most two. "
            "Use set_focus in accept mode only for the user's own accepted "
            "wording. Use record_intervention for at most one intervention lifecycle update. "
            "Call independent action tools together when possible. Tool validation errors explain "
            "what must be corrected. Do not describe a durable state change without calling its "
            "tool. Never call a tool merely to classify the conversational process. Keep the final "
            "reply under 1,200 characters." + return_guidance + formulation_guidance
        )
        deps = TurnContext(
            memory=self.memory,
            user_text=text,
            available_memory=available_memory,
            active_interventions=active_interventions,
        )
        agent = Agent[TurnContext, str](
            self.model,
            deps_type=TurnContext,
            output_type=str,
            instructions=instructions,
            retries={"tools": 2, "output": 2},
        )

        @agent.tool(sequential=True)
        def search_memory(ctx: RunContext[TurnContext], query: ShortText) -> dict[str, object]:
            """Search active longitudinal claims and safe historical excerpts."""
            _ensure_unused_tool(ctx.deps.actions, "search_memory")
            found = ctx.deps.memory.working_context(query)
            claims = [*found.confirmed_memory[:5], *found.hypotheses[:3]]
            ctx.deps.available_memory.update({item.id: item for item in claims})
            payload: dict[str, object] = {
                "claims": [item.model_dump(mode="json") for item in claims],
                "excerpts": found.relevant_excerpts[:3],
            }
            ctx.deps.actions.called_tools.add("search_memory")
            return _bounded_lookup(payload)

        @agent.tool(sequential=True)
        def record_memory(
            ctx: RunContext[TurnContext],
            observations: Annotated[list[MemoryObservation], Field(max_length=2)],
            offered_hypothesis: ShortText | None = None,
        ) -> dict[str, object]:
            """Stage sparse durable observations and an optional offered hypothesis."""
            _ensure_unused_tool(ctx.deps.actions, "record_memory")
            total = len(observations) + int(offered_hypothesis is not None)
            hypotheses = sum(
                item.kind in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS} for item in observations
            ) + int(offered_hypothesis is not None)
            if total == 0 or total > 2:
                raise ModelRetry("Record one or two durable memory items.")
            if hypotheses > 1:
                raise ModelRetry("Record at most one tentative pattern or hypothesis.")
            for observation in observations:
                if observation.confirmed_by_user and (
                    not _quote_in_text(observation.content, ctx.deps.user_text)
                    or observation.evidence_quote != observation.content
                ):
                    raise ModelRetry(
                        "A user-confirmed observation requires the same exact current-user "
                        "quote in content and evidence_quote; never mark an inference as "
                        "confirmed."
                    )
                if observation.kind in {
                    MemoryKind.FACT,
                    MemoryKind.PREFERENCE,
                    MemoryKind.EVENT,
                } and not _quote_in_text(observation.evidence_quote, ctx.deps.user_text):
                    raise ModelRetry(
                        "Facts, preferences, and events require an exact quote from this message."
                    )
                if observation.merge_into_id:
                    existing = ctx.deps.available_memory.get(observation.merge_into_id)
                    if existing is None or existing.kind is not observation.kind:
                        raise ModelRetry(
                            "A memory merge requires an available active claim of the same kind."
                        )
            ctx.deps.actions.observations = list(observations)
            ctx.deps.actions.offered_hypothesis = offered_hypothesis
            ctx.deps.actions.called_tools.add("record_memory")
            return {"staged": total}

        @agent.tool(sequential=True)
        def correct_memory(
            ctx: RunContext[TurnContext],
            corrections: Annotated[list[MemoryCorrection], Field(min_length=1, max_length=2)],
        ) -> dict[str, object]:
            """Stage corrections to existing active memory claims."""
            _ensure_unused_tool(ctx.deps.actions, "correct_memory")
            ids = [item.memory_id for item in corrections]
            if len(ids) != len(set(ids)):
                raise ModelRetry("Correct each memory ID at most once.")
            if set(ids) & set(ctx.deps.actions.confirmed_memory_ids):
                raise ModelRetry("Do not confirm and correct the same claim in one turn.")
            for correction in corrections:
                if correction.memory_id not in ctx.deps.available_memory:
                    raise ModelRetry(
                        "A correction requires an active claim from context or search_memory."
                    )
                if not _quote_in_text(correction.evidence_quote, ctx.deps.user_text):
                    raise ModelRetry(
                        "A correction requires an exact quote from the current message."
                    )
            ctx.deps.actions.corrections = list(corrections)
            ctx.deps.actions.called_tools.add("correct_memory")
            return {"staged": len(corrections)}

        @agent.tool(sequential=True)
        def confirm_hypotheses(
            ctx: RunContext[TurnContext],
            memory_ids: Annotated[list[str], Field(min_length=1, max_length=5)],
            evidence_quote: ShortText,
        ) -> dict[str, object]:
            """Stage explicit user confirmation of active tentative claims."""
            _ensure_unused_tool(ctx.deps.actions, "confirm_hypotheses")
            if len(memory_ids) != len(set(memory_ids)):
                raise ModelRetry("Confirm each hypothesis ID at most once.")
            if set(memory_ids) & {item.memory_id for item in ctx.deps.actions.corrections}:
                raise ModelRetry("Do not confirm and correct the same claim in one turn.")
            for item_id in memory_ids:
                item = ctx.deps.available_memory.get(item_id)
                if (
                    item is None
                    or item.status is not MemoryStatus.AGENT_HYPOTHESIS
                    or item.kind not in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS}
                ):
                    raise ModelRetry(
                        "Confirmation requires an active hypothesis from context or search_memory."
                    )
            if not _quote_in_text(evidence_quote, ctx.deps.user_text):
                raise ModelRetry(
                    "Hypothesis confirmation requires an exact quote from the current message."
                )
            ctx.deps.actions.confirmed_memory_ids = list(memory_ids)
            ctx.deps.actions.confirmation_evidence_quote = evidence_quote
            ctx.deps.actions.called_tools.add("confirm_hypotheses")
            return {"staged": len(memory_ids)}

        @agent.tool(sequential=True)
        def set_focus(
            ctx: RunContext[TurnContext],
            mode: FocusMode,
            focus: ShortText,
            evidence_quote: ShortText | None = None,
        ) -> dict[str, str]:
            """Stage a proposed focus or the user's accepted focus."""
            _ensure_unused_tool(ctx.deps.actions, "set_focus")
            if mode is FocusMode.ACCEPT and (
                not _quote_in_text(focus, ctx.deps.user_text)
                or not _quote_in_text(evidence_quote, ctx.deps.user_text)
            ):
                raise ModelRetry(
                    "An accepted focus and its evidence must be exact text from this message."
                )
            ctx.deps.actions.focus_mode = mode
            ctx.deps.actions.focus = focus
            ctx.deps.actions.focus_evidence_quote = evidence_quote
            ctx.deps.actions.called_tools.add("set_focus")
            return {"staged": mode.value}

        @agent.tool(sequential=True)
        def record_intervention(
            ctx: RunContext[TurnContext], action: InterventionAction
        ) -> dict[str, str]:
            """Stage one offered, agreed, tried, declined, or stopped intervention."""
            _ensure_unused_tool(ctx.deps.actions, "record_intervention")
            if action.skill is TherapeuticSkill.REPAIR:
                raise ModelRetry("Repair is conversational behavior, not an intervention record.")
            unknown_links = set(action.linked_memory_ids or []) - set(ctx.deps.available_memory)
            if unknown_links:
                raise ModelRetry("Linked memory IDs must come from context or search_memory.")
            if action.record_id:
                current = ctx.deps.active_interventions.get(action.record_id)
                if current is None or not valid_intervention_transition(
                    current.state, action.state
                ):
                    raise ModelRetry(
                        "Update an active intervention through a valid state transition."
                    )
                if action.skill.value != current.skill:
                    raise ModelRetry(
                        "An intervention update must keep the record's original skill."
                    )
            elif action.state not in {
                InterventionState.OFFERED,
                InterventionState.AGREED,
            }:
                raise ModelRetry("A new intervention must be offered or agreed.")
            elif pending_intervention and action.skill.value == pending_intervention.skill:
                raise ModelRetry(
                    "Update or stop the pending intervention instead of creating another."
                )
            if (
                action.record_id is not None or action.state is InterventionState.AGREED
            ) and not _quote_in_text(action.evidence_quote, ctx.deps.user_text):
                raise ModelRetry("An agreed or updated intervention requires an exact user quote.")
            ctx.deps.actions.intervention = action
            ctx.deps.actions.called_tools.add("record_intervention")
            return {"staged": action.state.value}

        @agent.output_validator
        def validate_reply(output: str) -> str:
            reply = output.strip()
            if not reply:
                raise ModelRetry("Return a non-empty visible reply.")
            if len(reply) > 1_200:
                raise ModelRetry("Keep the visible reply under 1,200 characters.")
            return reply

        async def event_stream_handler(
            ctx: RunContext[TurnContext],
            events: AsyncIterable[AgentStreamEvent],
        ) -> None:
            if on_event is None:
                await _consume_model_events(ctx, events)
            else:
                await _stream_model_events(ctx, events, on_event)

        result = agent.run_sync(
            text,
            deps=deps,
            message_history=history,
            usage_limits=TURN_LIMITS,
            event_stream_handler=event_stream_handler,
        )
        reply = result.output
        if on_event is not None:
            on_event(TurnStreamEvent(TurnStreamKind.REPLY, reply))
        actions = deps.actions
        run_messages = _persisted_run_messages(result.new_messages())
        tool_trace = _format_tool_trace(run_messages)
        session.last_context_tokens = _estimate_context_tokens(
            self.protocol.instructions,
            _bounded_context_json(context),
            [*history, *run_messages],
            "",
        )
        warning_threshold = math.floor(self.input_token_budget * CONTEXT_WARNING_RATIO)
        if session.last_context_tokens >= warning_threshold and not session.context_warning_sent:
            session.context_warning_sent = True
            warning = self._context_warning_notice()
            notice = f"{notice}\n{warning}" if notice else warning
        with self.memory.transaction():
            evidence_id = self.memory.save_turn(session, text, reply, run_messages, now)
            for correction in actions.corrections:
                self.memory.correct_memory(
                    correction.memory_id,
                    correction.replacement,
                    evidence_id,
                    now,
                )
                if correction.memory_id == app_state.pending_hypothesis_id:
                    app_state.pending_hypothesis_id = None
            correction_quotes = {
                " ".join(item.evidence_quote.split()).casefold() for item in actions.corrections
            }
            observations = [
                item
                for item in actions.observations
                if not item.evidence_quote
                or " ".join(item.evidence_quote.split()).casefold() not in correction_quotes
            ]
            if actions.offered_hypothesis:
                observations = [
                    *[
                        item
                        for item in observations
                        if item.kind not in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS}
                    ][:1],
                    MemoryObservation(
                        kind="hypothesis",
                        content=actions.offered_hypothesis,
                    ),
                ]
            saved_observations = self.memory.add_observations(
                observations,
                evidence_id,
                now,
                evidence_text=text,
            )
            for item in saved_observations:
                if (
                    item.status is MemoryStatus.USER_CONFIRMED
                    and item.id == app_state.pending_hypothesis_id
                ):
                    app_state.pending_hypothesis_id = None
            if actions.confirmed_memory_ids:
                self.memory.add_observations(
                    [
                        MemoryObservation(
                            kind=available_memory[item_id].kind,
                            content=available_memory[item_id].content,
                            evidence_quote=actions.confirmation_evidence_quote,
                            merge_into_id=item_id,
                        )
                        for item_id in actions.confirmed_memory_ids
                    ],
                    evidence_id,
                    now,
                    evidence_text=text,
                )
            for item_id in actions.confirmed_memory_ids:
                self.memory.confirm_memory(item_id, now)
                if item_id == app_state.pending_hypothesis_id:
                    app_state.pending_hypothesis_id = None
            if actions.offered_hypothesis:
                offered = next(
                    (
                        item
                        for item in saved_observations
                        if item.kind.value == "hypothesis"
                        and item.content == actions.offered_hypothesis
                    ),
                    None,
                )
                if offered is not None:
                    app_state.pending_hypothesis_id = offered.id
            formulation = self.memory.load_formulation()
            formulation_changed = False
            if actions.focus_mode is FocusMode.PROPOSE and actions.focus:
                formulation.proposed_focus = actions.focus
                formulation_changed = True
            if actions.focus_mode is FocusMode.ACCEPT and actions.focus:
                formulation.current_focus = actions.focus
                formulation.proposed_focus = None
                formulation_changed = True
            if formulation_changed:
                self.memory.save_formulation(formulation, now)
            if actions.intervention:
                action = actions.intervention
                if action.record_id:
                    updated = self.memory.update_intervention(
                        action.record_id,
                        state=action.state,
                        evidence_message_id=evidence_id,
                        description=action.description,
                        prediction=action.prediction,
                        linked_memory_ids=action.linked_memory_ids,
                        outcome=action.outcome,
                        user_appraisal=action.user_appraisal,
                        follow_up_at=action.follow_up_at,
                        now=now,
                    )
                    app_state.pending_intervention_id = (
                        updated.id
                        if updated.state in {InterventionState.OFFERED, InterventionState.AGREED}
                        else None
                    )
                elif action.state in {InterventionState.OFFERED, InterventionState.AGREED}:
                    created = self.memory.create_intervention(
                        skill=action.skill.value,
                        description=action.description,
                        prediction=action.prediction,
                        state=action.state,
                        linked_memory_ids=action.linked_memory_ids or [],
                        evidence_message_id=evidence_id,
                        follow_up_at=action.follow_up_at,
                        now=now,
                    )
                    app_state.pending_intervention_id = created.id
            self.memory.save_app_state(app_state)
        return ChatTurn(reply, notice, tool_trace)

    def end(self, now: datetime | None = None) -> SessionRecord | None:
        session = self.memory.active_session()
        if session is None:
            return None
        return self._consolidate(
            session,
            now,
            end_reason=SessionEndReason.EXPLICIT,
        )

    def _current_session(self, now: datetime | None) -> SessionRecord:
        session = self.memory.active_session()
        if session is None:
            return self.memory.start_session(now)
        if self.memory.session_expired(session, now):
            self._consolidate(
                session,
                datetime.fromisoformat(session.last_activity_at),
                end_reason=SessionEndReason.INACTIVITY,
            )
            return self.memory.start_session(now)
        return session

    def _consolidate(
        self,
        session: SessionRecord,
        now: datetime | None = None,
        *,
        end_reason: SessionEndReason,
    ) -> SessionRecord:
        transcript = self.memory.session_transcript(session.id, limit_chars=16_000)
        if not transcript:
            formulation = self.memory.load_formulation()
            formulation.proposed_focus = None
            with self.memory.transaction():
                self.memory.save_formulation(formulation, now)
                return self.memory.close_session(
                    session,
                    end_reason=end_reason,
                    now=now,
                )
        existing_formulation = self.memory.load_formulation()
        all_memories = self.memory.list_memory()
        by_id = {item.id: item for item in all_memories}
        priority_ids = [
            item_id for ids in existing_formulation.evidence.values() for item_id in ids
        ]
        memories = list(
            {
                item.id: item
                for item in [
                    *(by_id[item_id] for item_id in priority_ids if item_id in by_id),
                    *all_memories,
                ]
            }.values()
        )[:50]
        existing_formulation.proposed_focus = None
        instructions = (
            "Consolidate one therapeutic conversation episode. Use only the transcript and "
            "listed memory claims. Preserve uncertainty, do not diagnose, and never turn an "
            "agent hypothesis into a confirmed fact. Return a concise reflection plus "
            "formulation_links that map formulation fields only to existing memory IDs. Do not "
            "write independent formulation prose or invent IDs. Link agent_hypothesis claims "
            "only under open_hypotheses; every other field accepts only user_confirmed or "
            "user_corrected claims. Omission preserves existing valid formulation links.\n\n"
            "Use formulation_unlinks only to remove an existing field-to-claim link that this "
            "episode explicitly makes obsolete or no longer useful; omission is not removal.\n\n"
            "Existing formulation:\n"
            + existing_formulation.model_dump_json(indent=2)
            + "\n\nAvailable claims:\n"
            + "\n".join(item.model_dump_json() for item in memories)
        )
        agent = Agent(
            self.model,
            output_type=SessionReflection,
            instructions=instructions,
            retries={"output": 2},
        )
        try:
            reflection = agent.run_sync(
                transcript,
                usage_limits=CONSOLIDATION_LIMITS,
                event_stream_handler=_consume_model_events,
            ).output
        except AgentRunError as error:
            with self.memory.transaction():
                self.memory.save_formulation(existing_formulation, now)
                return self.memory.close_session(
                    session,
                    consolidation_error=type(error).__name__,
                    end_reason=end_reason,
                    now=now,
                )
        with self.memory.transaction():
            self.memory.save_formulation_links(
                reflection.formulation_links,
                proposed_focus=None,
                current_focus=existing_formulation.current_focus,
                merge_existing=True,
                remove_links=reflection.formulation_unlinks,
                now=now,
            )
            return self.memory.close_session(
                session,
                summary=reflection.summary,
                themes=reflection.themes,
                interventions=reflection.interventions,
                user_response=reflection.user_response,
                open_questions=reflection.open_questions,
                end_reason=end_reason,
                now=now,
            )

    def _context_warning_notice(self) -> str:
        if self.locale == "it-IT":
            return (
                "Avviso: questa sessione è vicina al limite di contesto. "
                "Quando sarà necessario, ne aprirò automaticamente una nuova."
            )
        return (
            "Notice: this session is approaching its context limit. "
            "I will automatically start a new one when needed."
        )

    def _context_rollover_notice(self) -> str:
        if self.locale == "it-IT":
            return (
                "La sessione precedente ha raggiunto il limite di contesto ed è stata chiusa. "
                "Questo messaggio apre una nuova sessione."
            )
        return (
            "The previous session reached its context limit and was closed. "
            "This message starts a new session."
        )


def _estimate_context_tokens(
    protocol_instructions: str,
    longitudinal_context: str,
    history: list[ModelRequest | ModelResponse],
    user_text: str,
) -> int:
    serialized_history = ModelMessagesTypeAdapter.dump_json(history)
    character_count = (
        len(protocol_instructions.encode())
        + len(longitudinal_context.encode())
        + len(serialized_history)
        + len(user_text.encode())
    )
    estimated_text_tokens = math.ceil(character_count / 4 * TOKEN_ESTIMATE_MARGIN)
    return estimated_text_tokens + CONTEXT_TOOL_RESERVE_TOKENS


def _format_tool_trace(messages: list[ModelRequest | ModelResponse]) -> str | None:
    blocks: list[str] = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                blocks.append(f"TOOL INPUT · {part.tool_name}\n{_format_tool_value(part.args)}")
            elif isinstance(part, ToolReturnPart):
                blocks.append(
                    f"TOOL OUTPUT · {part.tool_name} · {part.outcome}\n"
                    f"{_format_tool_value(part.content)}"
                )
            elif isinstance(part, RetryPromptPart) and part.tool_name:
                blocks.append(
                    f"TOOL OUTPUT · {part.tool_name} · retry\n{_format_tool_value(part.content)}"
                )
    return "\n\n".join(blocks) or None


def _persisted_run_messages(
    messages: list[ModelRequest | ModelResponse],
) -> list[ModelRequest | ModelResponse]:
    return [
        replace(message, instructions=None)
        if isinstance(message, ModelRequest)
        else replace(
            message,
            parts=[part for part in message.parts if not isinstance(part, ThinkingPart)],
        )
        for message in messages
    ]


def _format_tool_value(value: object) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _quote_in_text(quote: str | None, text: str) -> bool:
    if not quote:
        return False
    return " ".join(quote.split()).casefold() in " ".join(text.split()).casefold()


def _ensure_unused_tool(actions: TurnActions, name: str) -> None:
    if name in actions.called_tools:
        raise ModelRetry(f"Call {name} at most once per turn.")


def _bounded_lookup(payload: dict[str, object]) -> dict[str, object]:
    claims = payload["claims"]
    excerpts = payload["excerpts"]
    assert isinstance(claims, list)
    assert isinstance(excerpts, list)
    while len(json.dumps(payload, ensure_ascii=False)) > MAX_LOOKUP_CHARS:
        if excerpts:
            excerpts.pop()
        elif claims:
            claims.pop()
        else:
            break
    return payload


def _has_formulation(context: WorkingContext) -> bool:
    formulation = context.formulation
    return bool(
        formulation.current_focus
        or formulation.proposed_focus
        or any(getattr(formulation, field_name) for field_name in FORMULATION_FIELDS)
    )


def _bounded_context_json(context: WorkingContext) -> str:
    bounded = context.model_copy(deep=True)
    while len(payload := bounded.model_dump_json(indent=2)) > MAX_CONTEXT_CHARS:
        for field_name in (
            "relevant_excerpts",
            "recent_sessions",
            "confirmed_memory",
            "hypotheses",
            "active_interventions",
        ):
            values = getattr(bounded, field_name)
            if values:
                values.pop()
                break
        else:
            for field_name in reversed(FORMULATION_FIELDS):
                values = getattr(bounded.formulation, field_name)
                if values:
                    values.pop()
                    ids = bounded.formulation.evidence.get(field_name, [])
                    if ids:
                        ids.pop()
                    break
            else:
                if bounded.formulation.proposed_focus:
                    bounded.formulation.proposed_focus = None
                elif bounded.formulation.current_focus:
                    bounded.formulation.current_focus = None
                else:
                    return bounded.model_dump_json(indent=2)
    return payload

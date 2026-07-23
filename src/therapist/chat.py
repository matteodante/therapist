"""Therapeutic conversation seam shared by the CLI and tests."""

from __future__ import annotations

from collections.abc import AsyncIterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_ai import (
    Agent,
    AgentStreamEvent,
    ModelRequest,
    ModelResponse,
    ModelRetry,
    RunContext,
    UsageLimits,
    UserPromptPart,
)
from pydantic_ai.exceptions import AgentRunError
from pydantic_ai.messages import TextPart
from pydantic_ai.models import Model

from therapist.memory import (
    FORMULATION_FIELDS,
    InterventionState,
    MemoryCorrection,
    MemoryKind,
    MemoryObservation,
    MemoryStore,
    SessionRecord,
    WorkingContext,
    valid_intervention_transition,
)
from therapist.protocol import ProtocolPack
from therapist.safety import SafetyController, SafetyState, crisis_message

MAX_CONTEXT_CHARS = 12_000
TURN_LIMITS = UsageLimits(request_limit=3, output_tokens_limit=3_000)
CONSOLIDATION_LIMITS = UsageLimits(request_limit=3, output_tokens_limit=5_000)
ShortText = Annotated[str, Field(min_length=1, max_length=500)]


async def _consume_model_events(
    _: RunContext[None], events: AsyncIterable[AgentStreamEvent]
) -> None:
    async for _ in events:
        pass


class ProcessStage(StrEnum):
    LISTEN = "listen"
    EXPLORE = "explore"
    FORMULATE = "formulate"
    INTERVENE = "intervene"
    REVIEW = "review"
    REPAIR = "repair"


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
    linked_memory_ids: list[str] = Field(default_factory=list, max_length=5)
    outcome: ShortText | None = None
    user_appraisal: ShortText | None = None
    follow_up_at: str | None = None


class TherapistReply(BaseModel):
    reply: str = Field(min_length=1, max_length=1_200)
    observations: list[MemoryObservation] = Field(default_factory=list, max_length=2)
    corrections: list[MemoryCorrection] = Field(default_factory=list, max_length=2)
    offered_hypothesis: ShortText | None = None
    confirmed_memory_ids: list[str] = Field(default_factory=list, max_length=5)
    confirmation_evidence_quote: ShortText | None = None
    proposed_focus: ShortText | None = None
    accepted_focus: ShortText | None = None
    focus_evidence_quote: ShortText | None = None
    process_stage: ProcessStage = ProcessStage.EXPLORE
    selected_skill: TherapeuticSkill | None = None
    intervention: InterventionAction | None = None

    @model_validator(mode="after")
    def keep_process_coherent(self) -> TherapistReply:
        if (
            sum(
                item.kind in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS}
                for item in self.observations
            )
            > 1
        ):
            raise ValueError("Record at most one hypothesis per turn.")
        if self.process_stage in {
            ProcessStage.INTERVENE,
            ProcessStage.REVIEW,
            ProcessStage.REPAIR,
        } and self.selected_skill is None:
            raise ValueError("Intervene, review, and repair stages require one selected skill.")
        if (
            self.selected_skill is TherapeuticSkill.REPAIR
            and self.process_stage is not ProcessStage.REPAIR
        ):
            raise ValueError("Repair skill requires repair process stage.")
        if self.intervention and self.selected_skill != self.intervention.skill:
            raise ValueError("Selected skill must match the intervention skill.")
        if self.intervention and self.process_stage not in {
            ProcessStage.INTERVENE,
            ProcessStage.REVIEW,
        }:
            raise ValueError("An intervention requires intervene or review process stage.")
        return self


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
    safety_state: SafetyState
    process_stage: ProcessStage = ProcessStage.LISTEN
    selected_skill: TherapeuticSkill | None = None


class ChatSession:
    def __init__(
        self,
        model: str | Model,
        protocol: ProtocolPack,
        memory: MemoryStore,
        locale: str,
    ) -> None:
        if locale not in protocol.locales:
            raise ValueError(f"Locale not supported by protocol: {locale}")
        self.model = model
        self.protocol = protocol
        self.memory = memory
        self.locale = locale
        self.safety = SafetyController()

    def respond(self, text: str, now: datetime | None = None) -> ChatTurn:
        assessment = self.safety.assess(text, self.locale)
        if assessment.state is not SafetyState.CLEAR:
            session = self._session_for_safety(now)
            reply = crisis_message(assessment, self.locale)
            messages = [
                ModelRequest(parts=[UserPromptPart(content=text)]),
                ModelResponse(parts=[TextPart(content=reply)]),
            ]
            self.memory.save_turn(session, text, reply, messages, now)
            return ChatTurn(reply, assessment.state)

        session = self._current_session(now)
        context = self.memory.working_context(text)
        history = self.memory.load_session_history(session.id)
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
        repair_needed = _needs_repair(text)
        app_state = self.memory.load_app_state()
        pending_hypothesis_id = app_state.pending_hypothesis_id
        available_hypothesis_ids = {item.id for item in context.hypotheses}
        if pending_hypothesis_id not in available_hypothesis_ids:
            pending_hypothesis_id = None
            app_state.pending_hypothesis_id = None
        confirmation_expected = bool(
            pending_hypothesis_id and _explicit_hypothesis_confirmation(text)
        )
        available_memory = {
            item.id: item for item in [*context.confirmed_memory, *context.hypotheses]
        }
        correction_candidates = {
            item_id: item
            for item_id, item in available_memory.items()
            if _shares_memory_terms(text, item.content)
        }
        correction_expected = bool(
            correction_candidates and _explicit_memory_correction(text)
        )
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
        agreement_expected = bool(
            pending_intervention and _explicit_intervention_agreement(text)
        )
        repair_guidance = (
            "\n\nThe user signaled a mismatch in the helping process. Set process_stage to "
            "repair and selected_skill to repair-misattunement. Acknowledge the specific mismatch "
            "without defensiveness, stop the prior technique, briefly check what you missed, and "
            "invite correction naturally. Do not propose another intervention."
            if repair_needed
            else ""
        )
        pacing_guidance = (
            "\n\nThe user asked for understanding before suggestions. Stay in exploration or "
            "formulation. Stay with their meaning, offer at most one short tentative hypothesis "
            "only if useful, and ask a focused question only if it helps them continue. Do not "
            "list possible explanations or offer an exercise."
            if _requests_understanding_before_advice(text, context)
            else ""
        )
        confirmation_guidance = (
            "\n\nThe current message explicitly confirms the last offered hypothesis. Return "
            f"{pending_hypothesis_id!r} in confirmed_memory_ids and copy the shortest exact "
            "confirming words into confirmation_evidence_quote."
            if confirmation_expected
            else ""
        )
        correction_guidance = (
            "\n\nThe user explicitly corrected earlier information. Use corrections with the "
            "matching existing memory ID and an exact quote from this message. Do not also store "
            "the replacement as a new observation."
            if correction_expected
            else ""
        )
        intervention_guidance = (
            "\n\nThe user explicitly accepted the pending intervention. Update intervention "
            f"{pending_intervention.id!r} to agreed with an exact evidence quote; do not create "
            "another record."
            if agreement_expected and pending_intervention
            else ""
        )
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
            + "\n\nReturn at most two durable memory observations: stable facts, preferences, "
            "recurring patterns, or consequential events likely to matter in a later session. "
            "Do not turn each sentence into memory. Every fact, preference, and event must "
            "include an exact "
            "evidence_quote copied from that message; add up to five short lexical aliases when "
            "they improve later retrieval. Use merge_into_id when an existing claim expresses the "
            "same meaning. For explicit corrections, use corrections with an existing ID instead "
            "of adding another observation. "
            "Patterns and interpretations must be hypotheses. Set proposed_focus only when the "
            "conversation suggests it, and copy accepted_focus exactly from the user's current "
            "message with an exact focus_evidence_quote. Return a hypothesis ID in "
            "confirmed_memory_ids only "
            "with an exact confirmation_evidence_quote when the current user message confirms that "
            "hypothesis; do not merely add a fact saying they agreed. Whenever the visible reply "
            "offers one reusable interpretation for confirmation, copy that concise interpretation "
            "into offered_hypothesis; otherwise leave it null. Record at most one intervention. "
            "A new offered intervention needs no user quote; an agreed or updated intervention "
            "requires an exact evidence_quote from the current message. Questions are optional; "
            "usually ask no more than one, but natural closely related questions are allowed. Do "
            "not fall into a repeated reflection-hypothesis-question template."
            + return_guidance
            + repair_guidance
            + pacing_guidance
            + confirmation_guidance
            + correction_guidance
            + intervention_guidance
            + formulation_guidance
        )
        agent = Agent(
            self.model,
            output_type=TherapistReply,
            instructions=instructions,
            retries={"output": 2},
        )

        @agent.output_validator
        def validate_turn_contract(output: TherapistReply) -> TherapistReply:
            if repair_needed and (
                output.process_stage is not ProcessStage.REPAIR
                or output.selected_skill is not TherapeuticSkill.REPAIR
                or output.intervention is not None
            ):
                raise ModelRetry("Repair the mismatch before continuing therapeutic work.")
            if confirmation_expected and (
                pending_hypothesis_id not in output.confirmed_memory_ids
                or not _quote_in_text(output.confirmation_evidence_quote, text)
            ):
                raise ModelRetry("Record the explicit confirmation of the pending hypothesis.")
            if correction_expected and not output.corrections:
                raise ModelRetry("Apply the user's explicit correction to an existing memory ID.")
            for correction in output.corrections:
                allowed_corrections = (
                    correction_candidates if correction_expected else available_memory
                )
                if correction.memory_id not in allowed_corrections or not _quote_in_text(
                    correction.evidence_quote, text
                ):
                    raise ModelRetry(
                        "A correction requires an existing memory ID and exact user quote."
                    )
            for observation in output.observations:
                if observation.merge_into_id:
                    existing = available_memory.get(observation.merge_into_id)
                    if existing is None or existing.kind is not observation.kind:
                        raise ModelRetry("Memory merge requires an existing ID of the same kind.")
            if output.confirmed_memory_ids and not _quote_in_text(
                output.confirmation_evidence_quote, text
            ):
                raise ModelRetry("Confirmed memory requires an exact user confirmation quote.")
            if output.accepted_focus and (
                not _quote_in_text(output.focus_evidence_quote, text)
                or not _quote_in_text(output.accepted_focus, text)
            ):
                raise ModelRetry("Accepted focus requires an exact supporting user quote.")
            action = output.intervention
            if agreement_expected and (
                action is None
                or action.record_id != pending_intervention.id
                or action.state is not InterventionState.AGREED
            ):
                raise ModelRetry("Update the pending intervention instead of creating a new one.")
            if (
                action
                and action.record_id is None
                and pending_intervention
                and action.skill.value == pending_intervention.skill
            ):
                raise ModelRetry("Update or stop the active intervention before creating another.")
            if action and (
                action.record_id is not None or action.state is InterventionState.AGREED
            ) and not _quote_in_text(action.evidence_quote, text):
                raise ModelRetry("Agreed or updated intervention requires an exact user quote.")
            if action and action.record_id:
                current = next(
                    (
                        item.state
                        for item in context.active_interventions
                        if item.id == action.record_id
                    ),
                    None,
                )
                if current is None or not valid_intervention_transition(current, action.state):
                    raise ModelRetry("Invalid intervention state transition.")
            return output

        result = agent.run_sync(
            text,
            message_history=history,
            usage_limits=TURN_LIMITS,
            event_stream_handler=_consume_model_events,
        )
        output = result.output
        with self.memory.transaction():
            evidence_id = self.memory.save_turn(
                session, text, output.reply, result.new_messages(), now
            )
            for correction in output.corrections:
                self.memory.correct_memory(
                    correction.memory_id,
                    correction.replacement,
                    evidence_id,
                    now,
                )
                if correction.memory_id == app_state.pending_hypothesis_id:
                    app_state.pending_hypothesis_id = None
            correction_quotes = {
                " ".join(item.evidence_quote.split()).casefold()
                for item in output.corrections
            }
            observations = [
                item
                for item in output.observations
                if not item.evidence_quote
                or " ".join(item.evidence_quote.split()).casefold()
                not in correction_quotes
            ]
            if output.offered_hypothesis:
                observations = [
                    *[
                        item
                        for item in observations
                        if item.kind not in {MemoryKind.PATTERN, MemoryKind.HYPOTHESIS}
                    ][:1],
                    MemoryObservation(
                        kind="hypothesis",
                        content=output.offered_hypothesis,
                    ),
                ]
            saved_observations = self.memory.add_observations(
                observations,
                evidence_id,
                now,
                evidence_text=text,
            )
            allowed_confirmations = {item.id for item in context.hypotheses}
            for item_id in output.confirmed_memory_ids:
                if item_id in allowed_confirmations:
                    self.memory.confirm_memory(item_id, now)
                    if item_id == app_state.pending_hypothesis_id:
                        app_state.pending_hypothesis_id = None
            if output.offered_hypothesis:
                offered = next(
                    (
                        item
                        for item in saved_observations
                        if item.kind.value == "hypothesis"
                        and item.content == output.offered_hypothesis
                    ),
                    None,
                )
                if offered is not None:
                    app_state.pending_hypothesis_id = offered.id
            formulation = self.memory.load_formulation()
            formulation_changed = False
            if output.proposed_focus:
                formulation.proposed_focus = output.proposed_focus
                formulation_changed = True
            if output.accepted_focus:
                formulation.current_focus = output.accepted_focus
                formulation.proposed_focus = None
                formulation_changed = True
            if formulation_changed:
                self.memory.save_formulation(formulation, now)
            if output.intervention:
                action = output.intervention
                if action.record_id:
                    active_ids = {item.id for item in context.active_interventions}
                    if action.record_id in active_ids:
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
                            if updated.state
                            in {InterventionState.OFFERED, InterventionState.AGREED}
                            else None
                        )
                elif action.state in {InterventionState.OFFERED, InterventionState.AGREED}:
                    created = self.memory.create_intervention(
                        skill=action.skill.value,
                        description=action.description,
                        prediction=action.prediction,
                        state=action.state,
                        linked_memory_ids=action.linked_memory_ids,
                        evidence_message_id=evidence_id,
                        follow_up_at=action.follow_up_at,
                        now=now,
                    )
                    app_state.pending_intervention_id = created.id
            self.memory.save_app_state(app_state)
        return ChatTurn(
            output.reply,
            SafetyState.CLEAR,
            output.process_stage,
            output.selected_skill,
        )

    def end(self, now: datetime | None = None) -> SessionRecord | None:
        session = self.memory.active_session()
        if session is None:
            return None
        return self._consolidate(session, now)

    def _current_session(self, now: datetime | None) -> SessionRecord:
        session = self.memory.active_session()
        if session is None:
            return self.memory.start_session(now)
        if self.memory.session_expired(session, now):
            self._consolidate(session, datetime.fromisoformat(session.last_activity_at))
            return self.memory.start_session(now)
        return session

    def _session_for_safety(self, now: datetime | None) -> SessionRecord:
        session = self.memory.active_session()
        if session is None:
            return self.memory.start_session(now)
        if self.memory.session_expired(session, now):
            # Never introduce a model call before deterministic crisis routing.
            formulation = self.memory.load_formulation()
            formulation.proposed_focus = None
            with self.memory.transaction():
                self.memory.save_formulation(
                    formulation, datetime.fromisoformat(session.last_activity_at)
                )
                self.memory.close_session(
                    session, now=datetime.fromisoformat(session.last_activity_at)
                )
            return self.memory.start_session(now)
        return session

    def _consolidate(
        self, session: SessionRecord, now: datetime | None = None
    ) -> SessionRecord:
        transcript = self.memory.session_transcript(session.id, limit_chars=16_000)
        if not transcript:
            formulation = self.memory.load_formulation()
            formulation.proposed_focus = None
            with self.memory.transaction():
                self.memory.save_formulation(formulation, now)
                return self.memory.close_session(session, now=now)
        existing_formulation = self.memory.load_formulation()
        all_memories = self.memory.list_memory()
        by_id = {item.id: item for item in all_memories}
        priority_ids = [
            item_id
            for ids in existing_formulation.evidence.values()
            for item_id in ids
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
                now=now,
            )


def _quote_in_text(quote: str | None, text: str) -> bool:
    if not quote:
        return False
    return " ".join(quote.split()).casefold() in " ".join(text.split()).casefold()


def _needs_repair(text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    signals = (
        "non hai capito",
        "non mi hai capito",
        "non è quello che intendo",
        "troppi consigli",
        "non mi è servito",
        "non mi aiuta",
        "you didn't understand",
        "you did not understand",
        "that's not what i mean",
        "too much advice",
        "it didn't help",
        "this is not helping",
    )
    return any(signal in normalized for signal in signals)


def _explicit_hypothesis_confirmation(text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    signals = (
        "mi torna",
        "questa ipotesi è giusta",
        "questa ipotesi mi sembra giusta",
        "quel pattern mi torna",
        "that pattern fits",
        "that hypothesis fits",
        "that explanation fits",
        "yes, that fits",
        "yes that fits",
    )
    return any(signal in normalized for signal in signals)


def _explicit_memory_correction(text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    signals = (
        "devo correggere",
        "mi correggo:",
        "quello che ti avevo detto non è",
        "avevo detto una cosa sbagliata",
        "i need to correct",
        "let me correct",
        "what i told you was wrong",
        "i said that incorrectly",
    )
    return any(signal in normalized for signal in signals)


def _explicit_intervention_agreement(text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    if any(term in normalized for term in ("non mi va", "non lo farei", "won't try")):
        return False
    signals = (
        "l'idea mi va",
        "lo farei",
        "voglio provarci",
        "questo sì",
        "va bene, provo",
        "i'll try",
        "i will try",
        "that works for me",
        "i agree to try",
    )
    return any(signal in normalized for signal in signals)


def _has_formulation(context: WorkingContext) -> bool:
    formulation = context.formulation
    return bool(
        formulation.current_focus
        or formulation.proposed_focus
        or any(getattr(formulation, field_name) for field_name in FORMULATION_FIELDS)
    )


def _shares_memory_terms(text: str, memory: str) -> bool:
    def terms(value: str) -> set[str]:
        return {
            normalized
            for token in value.casefold().split()
            if len(normalized := token.strip(".,;:!?")) >= 4
        }

    return bool(terms(text) & terms(memory))


def _requests_understanding_before_advice(text: str, context: WorkingContext) -> bool:
    normalized = " ".join(text.casefold().split())
    signals = (
        "prima di darmi consigli",
        "prima dei consigli",
        "prima di suggerire",
        "capire prima",
        "understand it before suggesting",
        "understand before suggesting",
        "understanding before advice",
        "understand me before advice",
    )
    if any(signal in normalized for signal in signals):
        return True
    preference_terms = ("before advice", "prima dei consigli", "prima di suggerimenti")
    return any(
        any(term in item.content.casefold() for term in preference_terms)
        for item in context.confirmed_memory
        if item.kind.value == "preference"
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

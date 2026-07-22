"""Therapeutic conversation seam shared by the CLI and tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, ModelRequest, ModelResponse, UserPromptPart
from pydantic_ai.messages import TextPart
from pydantic_ai.models import Model

from therapist.memory import (
    CaseFormulation,
    MemoryObservation,
    MemoryStore,
    SessionRecord,
)
from therapist.protocol import ProtocolPack
from therapist.safety import SafetyController, SafetyState, crisis_message

MAX_CONTEXT_CHARS = 12_000


class TherapistReply(BaseModel):
    reply: str = Field(min_length=1, max_length=1_200)
    observations: list[MemoryObservation] = Field(default_factory=list)
    offered_hypothesis: str | None = None
    confirmed_memory_ids: list[str] = Field(default_factory=list)
    proposed_focus: str | None = None

    @field_validator("reply")
    @classmethod
    def keep_one_conversational_question(cls, value: str) -> str:
        if value.count("?") > 1:
            raise ValueError("Ask at most one question in each reply.")
        return value


class SessionReflection(BaseModel):
    summary: str
    themes: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    user_response: str = ""
    open_questions: list[str] = Field(default_factory=list)
    formulation: CaseFormulation


@dataclass(frozen=True)
class ChatTurn:
    text: str
    safety_state: SafetyState


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
                        "acknowledge that the old formulation may no longer fit, and use your one "
                        "question to ask what changed and what happened with any prior experiment. "
                        "Do not extend the old pattern to the new event until the user answers."
                    )
        instructions = (
            self.protocol.instructions
            + "\n\nLongitudinal context follows. Treat hypotheses as tentative and never "
            "claim a memory outside this context. User corrections override every older record.\n"
            + context.model_dump_json(indent=2)[:MAX_CONTEXT_CHARS]
            + "\n\nReturn a reply plus only concise memory observations supported by the "
            "user's current message. Facts, preferences, and events must be directly stated. "
            "Patterns and interpretations must be hypotheses. Set proposed_focus only when the "
            "conversation has explicitly established it. Return a hypothesis ID in "
            "confirmed_memory_ids only when the current user message explicitly confirms that "
            "hypothesis; do not merely add a fact saying they agreed. Whenever the visible reply "
            "offers one reusable interpretation for confirmation, copy that concise interpretation "
            "into offered_hypothesis; otherwise leave it null. Ask at most one question."
            + return_guidance
        )
        agent = Agent(
            self.model,
            output_type=TherapistReply,
            instructions=instructions,
            retries={"output": 2},
        )
        result = agent.run_sync(text, message_history=history)
        output = result.output
        evidence_id = self.memory.save_turn(
            session, text, output.reply, result.new_messages(), now
        )
        observations = output.observations
        if output.offered_hypothesis:
            observations = [
                *observations,
                MemoryObservation(
                    kind="hypothesis",
                    content=output.offered_hypothesis,
                ),
            ]
        self.memory.add_observations(observations, evidence_id, now)
        allowed_confirmations = {item.id for item in context.hypotheses}
        for item_id in output.confirmed_memory_ids:
            if item_id in allowed_confirmations:
                self.memory.confirm_memory(item_id, now)
        if output.proposed_focus:
            formulation = self.memory.load_formulation()
            formulation.current_focus = output.proposed_focus
            self.memory.save_formulation(formulation, now)
        return ChatTurn(output.reply, SafetyState.CLEAR)

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
            self.memory.close_session(
                session, now=datetime.fromisoformat(session.last_activity_at)
            )
            return self.memory.start_session(now)
        return session

    def _consolidate(
        self, session: SessionRecord, now: datetime | None = None
    ) -> SessionRecord:
        transcript = self.memory.session_transcript(session.id)
        if not transcript:
            return self.memory.close_session(session, now=now)
        instructions = (
            "Consolidate one therapeutic conversation episode. Use only the transcript and "
            "existing formulation. Preserve uncertainty, do not diagnose, and do not turn an "
            "agent hypothesis into a confirmed fact. Return a concise session reflection and a "
            "revised formulation.\n\nExisting formulation:\n"
            + self.memory.load_formulation().model_dump_json(indent=2)
        )
        agent = Agent(
            self.model,
            output_type=SessionReflection,
            instructions=instructions,
            retries={"output": 2},
        )
        try:
            reflection = agent.run_sync(transcript[-16_000:]).output
        except Exception:
            # The archive must survive provider or structured-output failures.
            return self.memory.close_session(session, now=now)
        self.memory.save_formulation(reflection.formulation, now)
        return self.memory.close_session(
            session,
            summary=reflection.summary,
            themes=reflection.themes,
            interventions=reflection.interventions,
            user_response=reflection.user_response,
            open_questions=reflection.open_questions,
            now=now,
        )

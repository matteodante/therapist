"""Deterministic tests for the clean-break epistemic memory model."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from therapist.memory import (
    AppState,
    CaseFormulation,
    ClaimCorrection,
    ClaimFit,
    ClaimLifecycle,
    ClaimOrigin,
    EvidenceQuality,
    HypothesisReview,
    InterventionDecision,
    InterventionState,
    MemoryError,
    MemoryKind,
    MemoryMode,
    MemoryStore,
    RetentionPolicy,
    SessionEndReason,
    UserReport,
)


def _message(store: MemoryStore, text: str, now: datetime | None = None) -> int:
    session = store.active_session() or store.start_session(now)
    return store.save_turn(session, text, "acknowledged", [], now)


def _report(
    store: MemoryStore,
    text: str,
    kind: MemoryKind = MemoryKind.FACT,
    now: datetime | None = None,
):
    message_id = _message(store, text, now)
    return store.add_user_reports(
        [UserReport(kind=kind, content=text, evidence_quote=text)],
        message_id,
        text,
        now,
    )[0]


def _hypothesis(store: MemoryStore, text: str, now: datetime | None = None):
    evidence = _report(store, f"Evidence for {text}", MemoryKind.EVENT, now)
    return store.add_hypothesis(
        text,
        linked_claim_ids=[evidence.id],
        evidence_message_ids=[evidence.evidence[0].message_id],
        now=now,
    )


def test_app_state_defaults_to_standard_memory_and_indefinite_retention() -> None:
    state = AppState()
    assert state.default_memory_mode is MemoryMode.STANDARD
    assert state.retention_policy == RetentionPolicy()


def test_retention_policy_rejects_zero_days() -> None:
    with pytest.raises(ValidationError):
        RetentionPolicy(raw_message_days=0)


def test_user_statement_is_a_report_not_external_truth(tmp_path) -> None:
    item = _report(MemoryStore(tmp_path), "I live in Rome")
    assert item.kind is MemoryKind.FACT
    assert item.origin is ClaimOrigin.USER_STATEMENT
    assert item.fit is ClaimFit.NOT_APPLICABLE
    assert item.evidence[0].quality is EvidenceQuality.EXACT_QUOTE


def test_user_report_requires_exact_current_message_quote(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    message_id = _message(store, "I live in Rome")
    with pytest.raises(ValueError, match="exact"):
        store.add_user_reports(
            [
                UserReport(
                    kind=MemoryKind.FACT,
                    content="I live in Milan",
                    evidence_quote="I live in Milan",
                )
            ],
            message_id,
            "I live in Rome",
        )


def test_user_report_rejects_model_paraphrase(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    message_id = _message(store, "I prefer shorter answers")
    with pytest.raises(ValueError, match="exact evidence quote"):
        store.add_user_reports(
            [
                UserReport(
                    kind=MemoryKind.PREFERENCE,
                    content="The user values brevity",
                    evidence_quote="I prefer shorter answers",
                )
            ],
            message_id,
            "I prefer shorter answers",
        )


def test_user_report_limit_is_two(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    with pytest.raises(ValueError, match="two"):
        store.add_user_reports(
            [
                UserReport(kind=MemoryKind.FACT, content=value, evidence_quote=value)
                for value in ("one", "two", "three")
            ],
            1,
            "one two three",
        )


def test_hypothesis_starts_unreviewed_and_remains_hypothesis_after_fits(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _hypothesis(store, "Avoidance may reduce distress briefly")
    message_id = _message(store, "Yes, that fits")
    reviewed, reports = store.review_hypotheses(
        [
            HypothesisReview(
                memory_id=item.id,
                fit=ClaimFit.FITS,
                evidence_quote="that fits",
            )
        ],
        message_id,
        "Yes, that fits",
    )
    assert reviewed[0].origin is ClaimOrigin.AGENT_HYPOTHESIS
    assert reviewed[0].fit is ClaimFit.FITS
    assert reports == []


@pytest.mark.parametrize(
    "fit",
    [ClaimFit.PARTLY_FITS, ClaimFit.DOES_NOT_FIT, ClaimFit.UNSURE],
)
def test_hypothesis_fit_variants_are_preserved(tmp_path, fit: ClaimFit) -> None:
    store = MemoryStore(tmp_path)
    item = _hypothesis(store, "A tentative pattern")
    message_id = _message(store, "This is my review")
    reviewed, _ = store.review_hypotheses(
        [
            HypothesisReview(
                memory_id=item.id,
                fit=fit,
                evidence_quote="This is my review",
            )
        ],
        message_id,
        "This is my review",
    )
    assert reviewed[0].fit is fit
    assert reviewed[0].origin is ClaimOrigin.AGENT_HYPOTHESIS


def test_partly_fits_can_create_distinct_exact_user_statement(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    hypothesis = _hypothesis(store, "I avoid every difficult conversation")
    text = "Partly: I avoid work calls"
    message_id = _message(store, text)
    _, reports = store.review_hypotheses(
        [
            HypothesisReview(
                memory_id=hypothesis.id,
                fit=ClaimFit.PARTLY_FITS,
                evidence_quote=text,
                accepted_wording_quote="I avoid work calls",
            )
        ],
        message_id,
        text,
    )
    assert reports[0].content == "I avoid work calls"
    assert reports[0].origin is ClaimOrigin.USER_STATEMENT


def test_review_requires_separate_claim_ids(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _hypothesis(store, "A pattern")
    review = HypothesisReview(
        memory_id=item.id,
        fit=ClaimFit.FITS,
        evidence_quote="yes",
    )
    with pytest.raises(ValueError, match="separate"):
        store.review_hypotheses([review, review], 1, "yes")


def test_correction_uses_replacement_quote_and_preserves_history(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _report(store, "I live in Rome")
    text = "That is wrong; I live in Turin"
    message_id = _message(store, text)
    corrected = store.correct_claim(
        ClaimCorrection(
            memory_id=item.id,
            correction_quote="That is wrong",
            replacement_quote="I live in Turin",
        ),
        message_id,
        text,
    )
    assert corrected.id == item.id
    assert corrected.content == "I live in Turin"
    assert corrected.superseded_content == ["I live in Rome"]
    assert corrected.lifecycle is ClaimLifecycle.ACTIVE


def test_contradiction_without_replacement_supersedes_claim(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _report(store, "I live in Rome")
    text = "That is not true"
    corrected = store.correct_claim(
        ClaimCorrection(memory_id=item.id, correction_quote=text),
        _message(store, text),
        text,
    )
    assert corrected.lifecycle is ClaimLifecycle.SUPERSEDED
    assert store.list_claims() == []


def test_correction_rejects_invented_replacement(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _report(store, "I live in Rome")
    text = "That is wrong"
    with pytest.raises(ValueError, match="replacement"):
        store.correct_claim(
            ClaimCorrection(
                memory_id=item.id,
                correction_quote=text,
                replacement_quote="I live in Turin",
            ),
            _message(store, text),
            text,
        )


def test_forgetting_archives_and_removes_formulation_link(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _report(store, "Calls are difficult")
    store.save_formulation_links({"presenting_concerns": [item.id]})
    store.forget_claim(item.id)
    assert store.list_claims() == []
    assert store.load_formulation().presenting_concerns == []


def test_incompatible_active_claims_are_linked_as_conflicts(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    first = _report(store, "I live in Rome")
    second = _report(store, "I live in Milan")
    assert first.id in second.conflict_ids
    saved_first = next(item for item in store.list_claims() if item.id == first.id)
    assert second.id in saved_first.conflict_ids
    context = store.retrieve_case_context("Where do I live?")
    assert {tuple(conflict.claim_ids) for conflict in context.conflicts}


def test_different_numbers_negations_dates_people_and_places_do_not_merge(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    values = (
        "I called 2 times",
        "I called 3 times",
        "I attend work events",
        "I do not attend work events",
        "I met Alice in Rome in March",
        "I met Bruno in Milan in April",
    )
    for value in values:
        _report(store, value)
    assert len(store.list_claims()) == len(values)


def test_does_not_fit_hypothesis_is_excluded_from_formulation(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _hypothesis(store, "A rejected pattern")
    message_id = _message(store, "No, that does not fit")
    store.review_hypotheses(
        [
            HypothesisReview(
                memory_id=item.id,
                fit=ClaimFit.DOES_NOT_FIT,
                evidence_quote="does not fit",
            )
        ],
        message_id,
        "No, that does not fit",
    )
    formulation = store.save_formulation_links({"open_hypotheses": [item.id]})
    assert formulation.open_hypotheses == []


def test_descriptive_formulation_rejects_agent_hypothesis(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _hypothesis(store, "A tentative concern")
    formulation = store.save_formulation_links({"presenting_concerns": [item.id]})
    assert formulation.presenting_concerns == []


def test_formulation_omission_preserves_links_and_explicit_unlink_removes(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _report(store, "Work calls are hard")
    store.save_formulation_links({"presenting_concerns": [item.id]})
    kept = store.save_formulation_links({}, merge_existing=True)
    assert kept.presenting_concerns == [item.content]
    removed = store.save_formulation_links(
        {},
        merge_existing=True,
        remove_links={"presenting_concerns": [item.id]},
    )
    assert removed.presenting_concerns == []


def test_process_preference_and_support_choice_require_exact_evidence(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    text = "I want shorter replies and I want to speak with a psychologist"
    message_id = _message(store, text)
    preference = store.record_process_preference(
        "I want shorter replies",
        "I want shorter replies",
        message_id,
        text,
    )
    support = store.record_support_choice(
        "I want to speak with a psychologist",
        "I want to speak with a psychologist",
        message_id,
        text,
    )
    assert preference.evidence.quote == "I want shorter replies"
    assert support.evidence.quote == "I want to speak with a psychologist"


def test_intervention_is_updated_in_place_with_outcome_and_harm(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    item = _report(store, "I avoid calls")
    record = store.create_intervention(
        skill="change-avoidance-behavior",
        description="Make one short call",
        state=InterventionState.AGREED,
        linked_claim_ids=[item.id],
        evidence_message_id=1,
        consent_quote="yes",
    )
    updated = store.update_intervention(
        record.id,
        state=InterventionState.TRIED,
        evidence_message_id=2,
        outcome="I made the call",
        unwanted_effects="I felt ashamed afterward",
        decision=InterventionDecision.ADAPT,
    )
    assert updated.id == record.id
    assert updated.outcome == "I made the call"
    assert updated.unwanted_effects == "I felt ashamed afterward"
    assert len(store.list_interventions()) == 1


def test_invalid_intervention_transition_is_rejected(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    record = store.create_intervention(
        skill="solve-practical-problems",
        description="List two options",
        state=InterventionState.OFFERED,
        linked_claim_ids=[],
        evidence_message_id=1,
    )
    with pytest.raises(ValueError, match="Invalid"):
        store.update_intervention(
            record.id,
            state=InterventionState.TRIED,
            evidence_message_id=2,
        )


def test_clean_break_rejects_previous_schema_without_migration(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    store._write_state("schema_version", b"2")
    with pytest.raises(MemoryError, match="migration is not supported"):
        MemoryStore(tmp_path)


def test_encrypted_database_does_not_contain_plaintext(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    _report(store, "sensitive-memory-marker")
    assert b"sensitive-memory-marker" not in store.database_path.read_bytes()


def test_ephemeral_store_creates_no_files(tmp_path) -> None:
    store = MemoryStore(tmp_path, ephemeral=True)
    _report(store, "Only for this process")
    assert not list(tmp_path.iterdir())


def test_session_history_and_tool_messages_are_round_tripped(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    store.save_turn(session, "hello", "hi", [])
    assert "hello" in store.session_transcript(session.id)
    assert store.load_session_history(session.id) == []


def test_session_can_close_with_explicit_reason(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    closed = store.close_session(session, end_reason=SessionEndReason.EXPLICIT)
    assert closed.end_reason is SessionEndReason.EXPLICIT
    assert closed.ended_at is not None


def test_export_contains_epistemic_and_governance_state(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    _report(store, "I like concise questions")
    exported = store.export()
    assert exported["schema_version"] == "3"
    assert exported["claims"][0]["origin"] == "user_statement"
    assert "semantic_index" not in exported


def test_unknown_app_state_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AppState.model_validate({"unknown": True})


def test_selective_session_deletion_propagates_to_messages(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    session = store.start_session()
    store.save_turn(session, "delete me", "ok", [])
    store.close_session(session)
    assert store.delete_session(session.id)
    assert store.list_sessions() == []
    assert "delete me" not in str(store.export())


def test_delete_before_removes_old_session_and_keeps_new(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    old = datetime(2024, 1, 1, tzinfo=UTC)
    session = store.start_session(old)
    store.save_turn(session, "old", "old", [], old)
    store.close_session(session, now=old)
    result = store.delete_before(datetime(2025, 1, 1, tzinfo=UTC))
    assert result["sessions"] == 1


def test_delete_before_accepts_cli_style_naive_iso_date(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    old = datetime(2024, 1, 1, tzinfo=UTC)
    session = store.start_session(old)
    store.close_session(session, now=old)
    assert store.delete_before(datetime(2025, 1, 1))["sessions"] == 1


def test_retention_dry_run_does_not_delete_messages(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    old = datetime.now(UTC) - timedelta(days=20)
    session = store.start_session(old)
    store.save_turn(session, "old message", "reply", [], old)
    store.close_session(session, now=old)
    preview = store.apply_retention(RetentionPolicy(raw_message_days=10), dry_run=True)
    assert preview["messages"] == 2
    assert "old message" in str(store.export())


def test_retention_apply_removes_old_raw_messages(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    old = datetime.now(UTC) - timedelta(days=20)
    session = store.start_session(old)
    store.save_turn(session, "old message", "reply", [], old)
    store.close_session(session, summary="Derived old summary", now=old)
    result = store.apply_retention(RetentionPolicy(raw_message_days=10))
    assert result["messages"] == 2
    assert "old message" not in str(store.export())
    assert "Derived old summary" not in str(store.export())


def test_stale_hypothesis_is_not_linked_into_active_formulation(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    old = datetime.now(UTC) - timedelta(days=200)
    item = _hypothesis(store, "An old tentative interpretation", old)
    formulation = store.save_formulation_links({"open_hypotheses": [item.id]})
    assert formulation == CaseFormulation(last_reviewed_at=formulation.last_reviewed_at)

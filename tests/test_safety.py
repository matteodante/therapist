from therapist.safety import SafetyController, SafetyState


def test_immediate_danger_disclosure_uses_italian_emergency_resource_without_score() -> None:
    result = SafetyController().assess(
        "Ho intenzione di farmi del male adesso e ho già un piano.", "it-IT"
    )

    assert result.state is SafetyState.IMMEDIATE_DANGER_DISCLOSED
    assert result.resource.emergency == "112"
    assert not hasattr(result, "score")


def test_us_safety_concern_uses_988_without_predicting_a_level() -> None:
    result = SafetyController().assess("I don't want to live anymore.", "en-US")

    assert result.state is SafetyState.SAFETY_CONCERN
    assert result.resource.crisis_line == "988"


def test_ordinary_distress_does_not_enter_crisis_flow() -> None:
    result = SafetyController().assess(
        "Sono stanco e questa settimana mi sento sotto pressione.", "it-IT"
    )

    assert result.state is SafetyState.CLEAR
    assert result.resource is None


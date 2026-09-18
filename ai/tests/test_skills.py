from app.skills import resolve_skill_message


def test_resolve_skill_message_fills_variables():
    prompt = "Generate a weekly update for {{project}} by the {{team}} team."
    result = resolve_skill_message(prompt, "/weekly-update project=mobile team=core")
    assert "mobile" in result
    assert "core" in result
    assert "{{" not in result


def test_unfilled_variable_remains_for_model_to_ask():
    result = resolve_skill_message("Update for {{project}}.", "/update")
    assert "{{project}}" in result


def test_trailing_text_is_appended_as_context():
    result = resolve_skill_message("Summarize {{topic}}.", "/summarize topic=login focus on MFA")
    assert "Additional context: focus on MFA" in result

"""Unit tests for Single Question Protocol."""

from edith.core.single_question import enforce_single_question


def test_single_question_zero_or_one_question():
    text_zero = "Everything is running smoothly, sir."
    assert enforce_single_question(text_zero) == text_zero

    text_one = "Would you like me to launch the application, sir?"
    assert enforce_single_question(text_one) == text_one


def test_single_question_multiple_questions_collapsed():
    text_multiple = "Would you like to open Chrome? Or shall I launch Firefox? Which one do you prefer?"
    result = enforce_single_question(text_multiple)
    assert result.count("?") == 1
    assert result.startswith("Would you like to open Chrome?")

"""
Tests for the ResponseEvaluator.

All tests run offline — no API key required.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluator import ResponseEvaluator


@pytest.fixture
def ev():
    return ResponseEvaluator()


@pytest.fixture
def base_state():
    return {"difficulty": "Normal", "secret_number": 42}


# ---------------------------------------------------------------------------
# Strategy keyword detection
# ---------------------------------------------------------------------------

def test_mentions_strategy_midpoint(ev):
    assert ev._mentions_strategy("Try the midpoint of your range.") is True


def test_mentions_strategy_binary(ev):
    assert ev._mentions_strategy("Use binary search to halve the range.") is True


def test_mentions_strategy_negative(ev):
    assert ev._mentions_strategy("Just pick something random.") is False


# ---------------------------------------------------------------------------
# Encouraging tone detection
# ---------------------------------------------------------------------------

def test_encouraging_tone_positive(ev):
    assert ev._encouraging_tone("Great job! Let's try guessing 37.") is True


def test_encouraging_tone_negative(ev):
    assert ev._encouraging_tone("Calculate the midpoint.") is False


# ---------------------------------------------------------------------------
# Guardrail tests
# ---------------------------------------------------------------------------

def test_guardrail_blocks_reveal_phrase(ev, base_state):
    assert ev._guardrails_passed("The answer is 42!", base_state) is False


def test_guardrail_blocks_secret_is_phrase(ev, base_state):
    assert ev._guardrails_passed("The secret is now known.", base_state) is False


def test_guardrail_blocks_secret_number(ev, base_state):
    # Response containing the exact secret number should fail
    assert ev._guardrails_passed("Try guessing 42.", base_state) is False


def test_guardrail_passes_clean_response(ev, base_state):
    assert ev._guardrails_passed(
        "Try the midpoint of your range — about halfway between your bounds!", base_state
    ) is True


def test_guardrail_passes_when_secret_is_none(ev):
    state = {"difficulty": "Easy"}
    assert ev._guardrails_passed("Try guessing 10.", state) is True


# ---------------------------------------------------------------------------
# Length check
# ---------------------------------------------------------------------------

def test_length_too_short_fails(ev, base_state):
    result = ev.evaluate("Try 10.", base_state)
    assert result["length_ok"] is False


def test_length_too_long_fails(ev, base_state):
    long_resp = "binary " * 130  # > 120 words
    result = ev.evaluate(long_resp, base_state)
    assert result["length_ok"] is False


def test_length_ok_passes(ev, base_state):
    resp = "Great work! Try the midpoint of your range — binary search is your best strategy here."
    result = ev.evaluate(resp, base_state)
    assert result["length_ok"] is True


# ---------------------------------------------------------------------------
# Overall quality score
# ---------------------------------------------------------------------------

def test_overall_quality_high_for_good_response(ev, base_state):
    resp = (
        "Great work! Use binary search: try the midpoint between your current lower "
        "and upper bounds for the best strategy."
    )
    result = ev.evaluate(resp, base_state)
    assert result["overall_quality"] >= 0.5


def test_overall_quality_low_for_bad_response(ev, base_state):
    # Fails guardrail AND mentions no strategy
    result = ev.evaluate("The answer is 42!", base_state)
    assert result["overall_quality"] < 0.5


def test_evaluate_returns_all_expected_keys(ev, base_state):
    keys = {"mentions_strategy", "encouraging_tone", "length_ok",
            "guardrails_passed", "overall_quality"}
    result = ev.evaluate("Try the midpoint of your range — great strategy!", base_state)
    assert keys.issubset(result.keys())


# ---------------------------------------------------------------------------
# Retrieval evaluation helper
# ---------------------------------------------------------------------------

def test_evaluate_retrieval_counts_docs(ev):
    docs = [{"id": "a", "tags": ["strategy"]}, {"id": "b", "tags": ["easy"]}]
    result = ev.evaluate_retrieval(docs, expected_tag="strategy")
    assert result["count"] == 2
    assert result["tag_hit_rate"] == 0.5


def test_evaluate_retrieval_empty(ev):
    result = ev.evaluate_retrieval([])
    assert result["has_results"] is False

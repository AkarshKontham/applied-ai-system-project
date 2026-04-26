"""
Tests for the RAG system.

These tests run entirely offline — no API key required.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_system import RAGSystem, _tokenize, _compute_tf, _cosine


# ---------------------------------------------------------------------------
# Helper / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rag():
    return RAGSystem(knowledge_base_path="knowledge_base/game_strategies.json")


# ---------------------------------------------------------------------------
# Tokenizer tests
# ---------------------------------------------------------------------------

def test_tokenize_lowercases():
    tokens = _tokenize("Binary Search STRATEGY")
    assert "binary" in tokens
    assert "search" in tokens
    assert "strategy" in tokens


def test_tokenize_strips_punctuation():
    tokens = _tokenize("too-high: guess!")
    assert "too" in tokens
    assert "high" in tokens
    assert "guess" in tokens


# ---------------------------------------------------------------------------
# TF tests
# ---------------------------------------------------------------------------

def test_tf_sums_to_one():
    tokens = ["a", "b", "a", "c"]
    tf = _compute_tf(tokens)
    assert abs(sum(tf.values()) - 1.0) < 1e-9


def test_tf_most_frequent_highest():
    tokens = ["binary", "binary", "search", "strategy"]
    tf = _compute_tf(tokens)
    assert tf["binary"] > tf["search"]


# ---------------------------------------------------------------------------
# Cosine similarity tests
# ---------------------------------------------------------------------------

def test_cosine_identical_vectors_is_one():
    v = {"a": 1.0, "b": 2.0}
    assert abs(_cosine(v, v) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors_is_zero():
    v1 = {"a": 1.0}
    v2 = {"b": 1.0}
    assert _cosine(v1, v2) == 0.0


def test_cosine_zero_vector_is_zero():
    assert _cosine({}, {"a": 1.0}) == 0.0


# ---------------------------------------------------------------------------
# RAG system tests
# ---------------------------------------------------------------------------

def test_rag_loads_documents(rag):
    assert len(rag.documents) >= 8


def test_rag_retrieve_returns_top_k(rag):
    results = rag.retrieve("binary search strategy", top_k=3)
    assert len(results) == 3


def test_rag_retrieve_returns_dicts_with_required_keys(rag):
    results = rag.retrieve("easy difficulty tips", top_k=1)
    doc = results[0]
    assert "id" in doc
    assert "title" in doc
    assert "content" in doc
    assert "tags" in doc


def test_rag_retrieve_easy_query_returns_easy_doc(rag):
    results = rag.retrieve("easy difficulty range 1 20", top_k=3)
    ids = [d["id"] for d in results]
    assert "easy_difficulty" in ids


def test_rag_retrieve_hard_query_returns_hard_doc(rag):
    results = rag.retrieve("hard difficulty range 1 100 tight budget", top_k=3)
    ids = [d["id"] for d in results]
    assert "hard_difficulty" in ids


def test_rag_retrieve_too_high_returns_too_high_doc(rag):
    results = rag.retrieve("too high upper bound adjust next guess", top_k=3)
    ids = [d["id"] for d in results]
    assert "too_high_response" in ids


def test_rag_retrieve_too_low_returns_too_low_doc(rag):
    results = rag.retrieve("too low lower bound adjust next guess", top_k=3)
    ids = [d["id"] for d in results]
    assert "too_low_response" in ids


def test_rag_retrieve_for_easy_game_state(rag):
    state = {"difficulty": "Easy", "last_hint": "No guess made yet", "attempts_left": 6}
    results = rag.retrieve_for_game_state(state)
    assert len(results) >= 1


def test_rag_retrieve_for_too_high_state(rag):
    state = {
        "difficulty": "Normal",
        "last_hint": "📉 Go LOWER!",
        "attempts_left": 5,
    }
    results = rag.retrieve_for_game_state(state)
    ids = [d["id"] for d in results]
    assert "too_high_response" in ids


def test_rag_format_context_contains_titles(rag):
    docs = rag.retrieve("binary search midpoint", top_k=2)
    context = rag.format_context(docs)
    assert "Relevant game knowledge" in context
    for doc in docs:
        assert doc["title"] in context

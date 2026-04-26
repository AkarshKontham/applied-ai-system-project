"""
RAG (Retrieval-Augmented Generation) system.

Loads a JSON knowledge base and retrieves the most relevant documents
for a query using TF-IDF vectors and cosine similarity.
No external vector database required.
"""

import json
import math
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal vector math helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-z0-9]+\b", text.lower())


def _compute_tf(tokens: List[str]) -> Dict[str, float]:
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens) or 1
    return {t: c / total for t, c in counts.items()}


def _build_idf(tokenized_docs: List[List[str]]) -> Dict[str, float]:
    n = len(tokenized_docs)
    df: Dict[str, int] = {}
    for tokens in tokenized_docs:
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (freq + 1)) + 1 for t, freq in df.items()}


def _to_tfidf(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = _compute_tf(tokens)
    return {t: f * idf.get(t, 1.0) for t, f in tf.items()}


def _cosine(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    shared = set(vec_a) & set(vec_b)
    dot = sum(vec_a[k] * vec_b[k] for k in shared)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Public RAG class
# ---------------------------------------------------------------------------

class RAGSystem:
    """Simple in-memory TF-IDF RAG over a JSON knowledge base."""

    def __init__(self, knowledge_base_path: str = "knowledge_base/game_strategies.json"):
        self.documents: List[Dict] = []
        self._doc_vecs: List[Dict[str, float]] = []
        self._idf: Dict[str, float] = {}
        self._load(knowledge_base_path)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _load(self, path: str) -> None:
        kb_path = Path(path)
        if not kb_path.exists():
            raise FileNotFoundError(f"Knowledge base not found at: {path}")

        with open(kb_path, "r", encoding="utf-8") as fh:
            self.documents = json.load(fh)

        tokenized: List[List[str]] = []
        for doc in self.documents:
            full_text = f"{doc['title']} {doc['content']} {' '.join(doc.get('tags', []))}"
            tokenized.append(_tokenize(full_text))

        self._idf = _build_idf(tokenized)
        self._doc_vecs = [_to_tfidf(tokens, self._idf) for tokens in tokenized]

        logger.info("RAG loaded %d documents from %s", len(self.documents), path)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """Return the top_k most relevant documents for the query."""
        q_tokens = _tokenize(query)
        q_vec = _to_tfidf(q_tokens, self._idf)

        scored: List[Tuple[float, int]] = [
            (_cosine(q_vec, doc_vec), i)
            for i, doc_vec in enumerate(self._doc_vecs)
        ]
        scored.sort(reverse=True)

        results = [self.documents[i] for _, i in scored[:top_k]]
        logger.debug(
            "RAG query=%r -> top docs: %s",
            query,
            [d["id"] for d in results],
        )
        return results

    def retrieve_for_game_state(self, game_state: Dict) -> List[Dict]:
        """Build a query from the current game state and retrieve documents."""
        parts: List[str] = []

        difficulty = game_state.get("difficulty", "")
        if difficulty:
            parts.append(f"{difficulty.lower()} difficulty range")

        last_hint = game_state.get("last_hint", "")
        if "high" in last_hint.lower():
            parts.append("too high upper bound adjust")
        elif "low" in last_hint.lower():
            parts.append("too low lower bound adjust")
        else:
            parts.append("first guess opening strategy midpoint")

        attempts_left = game_state.get("attempts_left", 5)
        if attempts_left <= 2:
            parts.append("limited attempts budget last guess")

        query = " ".join(parts)
        return self.retrieve(query, top_k=3)

    def format_context(self, docs: List[Dict]) -> str:
        """Format retrieved documents as a readable context block."""
        if not docs:
            return "No relevant knowledge retrieved."
        lines = ["Relevant game knowledge:"]
        for doc in docs:
            lines.append(f"- **{doc['title']}**: {doc['content']}")
        return "\n".join(lines)

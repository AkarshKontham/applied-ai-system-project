"""
Response evaluator.

Checks AI responses for quality (strategic content, length, tone) and
enforces guardrails (never reveal the secret number or say 'the answer is').
Returns a dict of individual check results plus an overall_quality score.
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_STRATEGY_WORDS = [
    "midpoint", "binary", "halfway", "middle", "halve", "half",
    "range", "between", "above", "below",
]
_POSITIVE_WORDS = [
    "great", "good", "nice", "well", "you can", "try", "let", "consider",
]
_REVEAL_PATTERNS = [
    re.compile(r"\bthe (secret|answer|number) is\b", re.IGNORECASE),
    re.compile(r"\bit is\s+\d+\b", re.IGNORECASE),
]


class ResponseEvaluator:
    """Evaluate AI hint responses for quality and safety."""

    def evaluate(self, response: str, game_state: Dict) -> Dict:
        """
        Run all checks and return a results dict including overall_quality (0-1).
        """
        checks = {
            "mentions_strategy": self._mentions_strategy(response),
            "encouraging_tone": self._encouraging_tone(response),
            "length_ok": 10 <= len(response.split()) <= 120,
            "guardrails_passed": self._guardrails_passed(response, game_state),
        }

        # Weighted aggregate
        weights = {
            "mentions_strategy": 0.35,
            "encouraging_tone": 0.15,
            "length_ok": 0.15,
            "guardrails_passed": 0.35,
        }
        overall = sum(weights[k] * (1.0 if v else 0.0) for k, v in checks.items())
        checks["overall_quality"] = round(overall, 3)

        if not checks["guardrails_passed"]:
            logger.warning("Guardrail violation in response: %.80s", response)

        logger.debug("Evaluation results: %s", checks)
        return checks

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _mentions_strategy(self, response: str) -> bool:
        lower = response.lower()
        return any(w in lower for w in _STRATEGY_WORDS)

    def _encouraging_tone(self, response: str) -> bool:
        lower = response.lower()
        return any(w in lower for w in _POSITIVE_WORDS)

    def _guardrails_passed(self, response: str, game_state: Dict) -> bool:
        for pattern in _REVEAL_PATTERNS:
            if pattern.search(response):
                return False

        secret = game_state.get("secret_number")
        if secret is not None:
            if re.search(rf"\b{re.escape(str(secret))}\b", response):
                logger.warning("Response contains secret number %s", secret)
                return False

        return True

    # ------------------------------------------------------------------
    # RAG retrieval evaluation (used in tests)
    # ------------------------------------------------------------------

    def evaluate_retrieval(
        self,
        retrieved_docs: List[Dict],
        expected_tag: Optional[str] = None,
    ) -> Dict:
        result: Dict = {"count": len(retrieved_docs), "has_results": len(retrieved_docs) > 0}
        if expected_tag and retrieved_docs:
            hits = sum(
                1 for d in retrieved_docs if expected_tag in d.get("tags", [])
            )
            result["tag_hit_rate"] = hits / len(retrieved_docs)
        return result

"""
AI Assistant with agentic workflow.

The agent follows four steps each time it is asked for a hint:
  1. Observe  – parse and validate the current game state
  2. Retrieve – RAG query to the knowledge base
  3. Generate – call Claude with game state + retrieved context
  4. Evaluate – quality-check the response; retry once if quality is too low

All interactions are logged via logger.py.
"""

import os
import re
import logging
from typing import Dict, List, Optional

import anthropic

from rag_system import RAGSystem
from evaluator import ResponseEvaluator
from logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a concise, encouraging strategy assistant for a number guessing game.

Rules you must follow:
- NEVER state or hint at the exact secret number.
- Give concrete, actionable advice (e.g., "Try guessing 37 — the midpoint of 25 and 50").
- Keep your response to 2-4 sentences.
- End your response with a confidence marker in this exact format: [confidence: X.X]
  where X.X is a decimal between 0.0 and 1.0 reflecting how sure you are your advice is useful.
"""


class AIAssistant:
    """
    Agentic hint generator.

    Uses RAG to enrich prompts with relevant game knowledge, then calls Claude
    to produce a personalised, actionable hint. A ResponseEvaluator checks
    quality and triggers one automatic retry if the first response is poor.
    """

    def __init__(
        self,
        rag: Optional[RAGSystem] = None,
        evaluator: Optional[ResponseEvaluator] = None,
    ) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("anthropic_api_key")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._rag = rag or RAGSystem()
        self._evaluator = evaluator or ResponseEvaluator()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_hint(self, game_state: Dict) -> Dict:
        """
        Run the full agentic loop and return a hint dict:
          {hint, confidence, quality, retrieved_docs, success, retried}
        """
        logger.info(
            "get_hint called: difficulty=%s attempts_left=%s",
            game_state.get("difficulty"),
            game_state.get("attempts_left"),
        )

        # Step 1: Observe – validate essential fields
        game_state = self._observe(game_state)

        # Step 2: Retrieve
        docs = self._rag.retrieve_for_game_state(game_state)
        context = self._rag.format_context(docs)

        # Step 3 + 4: Generate then Evaluate (with one retry)
        retried = False
        for attempt_num in range(2):
            raw = self._generate(game_state, context)
            if raw is None:
                return self._fallback(docs)

            evaluation = self._evaluator.evaluate(raw, game_state)
            quality = evaluation["overall_quality"]

            if quality >= 0.5 or attempt_num == 1:
                break

            # Quality too low on first try – refine context and retry
            logger.info("Quality %.2f below threshold; retrying with refined prompt", quality)
            context = self._refine_context(context, game_state)
            retried = True

        confidence = self._extract_confidence(raw)
        clean_hint = re.sub(r"\[confidence:\s*[\d.]+\]", "", raw).strip()

        logger.info("Hint ready: confidence=%.2f quality=%.2f retried=%s", confidence, quality, retried)

        return {
            "hint": clean_hint,
            "confidence": confidence,
            "quality": quality,
            "retrieved_docs": [d["id"] for d in docs],
            "success": True,
            "retried": retried,
        }

    def explain_difficulty(self, difficulty: str) -> Dict:
        """Return a strategy overview for the given difficulty."""
        docs = self._rag.retrieve(f"{difficulty.lower()} difficulty strategy tips range", top_k=3)
        context = self._rag.format_context(docs)

        prompt = (
            f"Give a brief strategy overview for {difficulty} difficulty in the number guessing game.\n\n"
            f"{context}"
        )
        raw = self._generate_raw(prompt)
        if raw is None:
            return {"explanation": f"Use binary search for {difficulty} difficulty.", "success": False}

        clean = re.sub(r"\[confidence:\s*[\d.]+\]", "", raw).strip()
        return {"explanation": clean, "success": True}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _observe(self, game_state: Dict) -> Dict:
        """Fill in sensible defaults for any missing game-state keys."""
        defaults = {
            "difficulty": "Normal",
            "range_low": 1,
            "range_high": 50,
            "attempts_used": 0,
            "attempts_left": 8,
            "last_hint": "No guess made yet",
            "score": 0,
        }
        return {**defaults, **game_state}

    def _generate(self, game_state: Dict, context: str) -> Optional[str]:
        prompt = self._build_prompt(game_state, context)
        return self._generate_raw(prompt)

    def _generate_raw(self, user_prompt: str) -> Optional[str]:
        try:
            response = self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except anthropic.APIError as exc:
            logger.error("Claude API error: %s", exc)
            return None

    def _build_prompt(self, game_state: Dict, context: str) -> str:
        return (
            f"Current game state:\n"
            f"- Difficulty: {game_state['difficulty']}\n"
            f"- Active range: {game_state['range_low']} to {game_state['range_high']}\n"
            f"- Attempts used: {game_state['attempts_used']}, "
            f"Attempts remaining: {game_state['attempts_left']}\n"
            f"- Last feedback: {game_state['last_hint']}\n"
            f"- Current score: {game_state['score']}\n\n"
            f"{context}\n\n"
            f"Give a helpful, strategic hint for the player's next guess."
        )

    def _refine_context(self, original_context: str, game_state: Dict) -> str:
        """Augment context with midpoint calculation advice on retry."""
        low = game_state.get("range_low", 1)
        high = game_state.get("range_high", 100)
        mid = (low + high) // 2
        extra = (
            f"\nAdditional note: The midpoint of the current range "
            f"({low} to {high}) is {mid}. Advise the player to guess {mid}."
        )
        return original_context + extra

    def _extract_confidence(self, text: str) -> float:
        match = re.search(r"\[confidence:\s*([\d.]+)\]", text, re.IGNORECASE)
        if match:
            try:
                return min(1.0, max(0.0, float(match.group(1))))
            except ValueError:
                pass
        return 0.7  # safe default if marker is absent

    def _fallback(self, docs: List[Dict]) -> Dict:
        return {
            "hint": (
                "I couldn't reach the AI right now. "
                "Try binary search: guess the midpoint of your current range!"
            ),
            "confidence": 0.5,
            "quality": 0.5,
            "retrieved_docs": [d["id"] for d in docs],
            "success": False,
            "retried": False,
        }

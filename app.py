"""
Number Guessing Game with AI Strategy Assistant.

Original project: a Streamlit number-guessing game used to practice
debugging AI-generated code (Modules 1-3).

Extended project: the game now includes an AI assistant powered by
Claude + RAG that gives personalized, strategic hints based on the
player's current game state.
"""

import os
import re
import random
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from logic_utils import get_range_for_difficulty, parse_guess, check_guess, update_score

# ---------------------------------------------------------------------------
# Optional AI components — degrade gracefully when API key is absent
# ---------------------------------------------------------------------------
_AI_IMPORT_ERROR: str = ""
try:
    from ai_assistant import AIAssistant
    from evaluator import ResponseEvaluator
    from logger import GameSessionLogger
    _AI_COMPONENTS_LOADED = True
except Exception as _exc:
    _AI_IMPORT_ERROR = str(_exc)
    _AI_COMPONENTS_LOADED = False

AI_AVAILABLE: bool = _AI_COMPONENTS_LOADED and bool(
    os.getenv("ANTHROPIC_API_KEY") or os.getenv("anthropic_api_key")
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Number Guessing Game + AI Assistant", page_icon="🎮")

st.title("🎮 Number Guessing Game")
st.caption(
    "A number-guessing game with an AI strategy assistant powered by Claude + RAG."
    if AI_AVAILABLE
    else "A number-guessing game. Set ANTHROPIC_API_KEY to enable the AI assistant."
)

# ---------------------------------------------------------------------------
# Sidebar — difficulty selector + AI status
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Settings")
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)

attempt_limit_map = {"Easy": 6, "Normal": 8, "Hard": 5}
attempt_limit = attempt_limit_map[difficulty]

low, high = get_range_for_difficulty(difficulty)
st.sidebar.caption(f"Range: {low} – {high}")
st.sidebar.caption(f"Max attempts: {attempt_limit}")

st.sidebar.divider()
if AI_AVAILABLE:
    st.sidebar.success("🤖 AI Assistant: ON")
else:
    st.sidebar.warning("🤖 AI Assistant: OFF\nSet ANTHROPIC_API_KEY to enable.")

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init_game() -> None:
    """Reset all game-related session state."""
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.last_feedback = "No guess made yet"
    # Track the narrowing bounds for the AI assistant
    st.session_state.range_low = low
    st.session_state.range_high = high


for key in ("secret", "attempts", "score", "status", "history", "last_feedback",
            "range_low", "range_high"):
    if key not in st.session_state:
        _init_game()
        break

# AI component instances — created once per session
if AI_AVAILABLE:
    if "ai_assistant" not in st.session_state:
        try:
            st.session_state.ai_assistant = AIAssistant()
            st.session_state.evaluator = ResponseEvaluator()
            st.session_state.session_logger = GameSessionLogger()
            st.session_state.session_logger.log_game_start(
                difficulty, st.session_state.range_low, st.session_state.range_high
            )
        except Exception as exc:
            st.sidebar.error(f"AI init failed: {exc}")
            AI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Debug expander (developer view)
# ---------------------------------------------------------------------------
with st.expander("🔍 Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts used:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Active range:", st.session_state.range_low, "–", st.session_state.range_high)
    st.write("Difficulty:", difficulty)
    st.write("Guess history:", st.session_state.history)

# ---------------------------------------------------------------------------
# Game info banner
# ---------------------------------------------------------------------------
attempts_left = attempt_limit - st.session_state.attempts
st.info(
    f"Guess a number between **{low}** and **{high}**. "
    f"Attempts remaining: **{attempts_left}**  |  Score: **{st.session_state.score}**"
)

# ---------------------------------------------------------------------------
# Input + action buttons
# ---------------------------------------------------------------------------
raw_guess = st.text_input("Enter your guess:", key=f"guess_input_{difficulty}")

col1, col2 = st.columns(2)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")

# ---------------------------------------------------------------------------
# New Game handler
# ---------------------------------------------------------------------------
if new_game:
    _init_game()
    if AI_AVAILABLE and "session_logger" in st.session_state:
        st.session_state.session_logger.log_game_start(
            difficulty, st.session_state.range_low, st.session_state.range_high
        )
    st.success("New game started!")
    st.rerun()

# ---------------------------------------------------------------------------
# Game-over guard
# ---------------------------------------------------------------------------
if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success("You already won this round. Press **New Game** to play again.")
    else:
        st.error("Game over. Press **New Game** to try again.")
    st.stop()

# ---------------------------------------------------------------------------
# Submit Guess handler
# ---------------------------------------------------------------------------
if submit:
    st.session_state.attempts += 1
    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.session_state.attempts -= 1  # don't count invalid input
        st.error(err)
    else:
        st.session_state.history.append(guess_int)

        outcome, message = check_guess(guess_int, st.session_state.secret)
        st.session_state.last_feedback = message

        # Narrow the tracked range for the AI assistant
        if outcome == "Too High":
            st.session_state.range_high = min(
                st.session_state.range_high, guess_int - 1
            )
        elif outcome == "Too Low":
            st.session_state.range_low = max(
                st.session_state.range_low, guess_int + 1
            )

        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        if AI_AVAILABLE and "session_logger" in st.session_state:
            st.session_state.session_logger.log_guess(
                guess=guess_int,
                outcome=outcome,
                attempts_used=st.session_state.attempts,
            )

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            st.success(
                f"🎉 Correct! The secret was **{st.session_state.secret}**. "
                f"Final score: **{st.session_state.score}**"
            )
            if AI_AVAILABLE and "session_logger" in st.session_state:
                st.session_state.session_logger.log_game_end(
                    won=True,
                    attempts_used=st.session_state.attempts,
                    score=st.session_state.score,
                )
        else:
            st.warning(message)
            if st.session_state.attempts >= attempt_limit:
                st.session_state.status = "lost"
                st.error(
                    f"Out of attempts! The secret was **{st.session_state.secret}**. "
                    f"Score: **{st.session_state.score}**"
                )
                if AI_AVAILABLE and "session_logger" in st.session_state:
                    st.session_state.session_logger.log_game_end(
                        won=False,
                        attempts_used=st.session_state.attempts,
                        score=st.session_state.score,
                    )

# ---------------------------------------------------------------------------
# AI Strategy Assistant panel
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🤖 AI Strategy Assistant")

if not AI_AVAILABLE:
    st.info(
        "The AI assistant is disabled. "
        "Add your `ANTHROPIC_API_KEY` to an `.env` file or environment variable to enable it."
    )
else:
    hint_col, explain_col = st.columns([2, 1])

    with hint_col:
        if st.button("Get AI Hint ✨", disabled=(st.session_state.status != "playing")):
            game_state = {
                "difficulty": difficulty,
                "range_low": st.session_state.range_low,
                "range_high": st.session_state.range_high,
                "attempts_used": st.session_state.attempts,
                "attempts_left": attempt_limit - st.session_state.attempts,
                "last_hint": st.session_state.last_feedback,
                "score": st.session_state.score,
                "secret_number": st.session_state.secret,  # used only for guardrail checks
            }

            with st.spinner("Thinking…"):
                result = st.session_state.ai_assistant.get_hint(game_state)

            eval_result = st.session_state.evaluator.evaluate(result["hint"], game_state)

            # Display the hint
            st.info(result["hint"])

            # Metrics row
            m1, m2, m3 = st.columns(3)
            m1.metric("AI Confidence", f"{result['confidence']:.0%}")
            m2.metric("Response Quality", f"{eval_result['overall_quality']:.0%}")
            m3.metric("Strategy Present", "Yes" if eval_result["mentions_strategy"] else "No")

            if result.get("retried"):
                st.caption("↩️ Response was auto-improved (retry triggered by low quality)")

            # Log the interaction
            st.session_state.session_logger.log_ai_hint(
                confidence=result["confidence"],
                quality=eval_result["overall_quality"],
                retrieved_docs=result["retrieved_docs"],
                success=result["success"],
            )

    with explain_col:
        if st.button("Explain Strategy 📖"):
            with st.spinner("Loading strategy…"):
                expl = st.session_state.ai_assistant.explain_difficulty(difficulty)
            st.write(expl["explanation"])

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption("Built with Streamlit + Claude + RAG  ·  Applied AI Systems Project")

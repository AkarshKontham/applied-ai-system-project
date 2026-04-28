# Number Guessing Game with AI Strategy Assistant

## Video Walkthrough

[Watch the Loom walkthrough](https://www.loom.com/share/255e15e7925a40c88c06e22c9f72d30d)

---

## Original Project (Modules 1–3)

**Original project name: Game Glitch Investigator**

The original project was a deliberately buggy Streamlit number-guessing game used as a debugging exercise. Students had to identify three logic errors (flipped hint labels, swapped difficulty ranges, and an off-by-one attempt counter), fix them, extract the core logic into a testable `logic_utils.py` module, and write pytest tests to verify the fixes.

---

## What This Project Does

This project extends the original game into a full AI system. Players guess a secret number within a difficulty-specific range, and an **AI Strategy Assistant** provides personalized, context-aware hints using:

- **RAG (Retrieval-Augmented Generation):** A TF-IDF knowledge base of game strategies is queried every time the player requests a hint. The retrieved documents are injected into the Claude prompt, grounding the AI's advice in proven strategies rather than raw generation.
- **Agentic Workflow:** The assistant follows a four-step loop — Observe → Retrieve → Generate → Evaluate — and automatically retries once if the first response quality is too low.
- **Reliability System:** A `ResponseEvaluator` checks every AI response for strategic content, appropriate length, encouraging tone, and guardrail compliance (e.g., never reveals the secret number). Confidence and quality scores are displayed live in the UI.

---

## Architecture Overview

```
┌───────────────────────────────────────────────────────┐
│              Streamlit Web App  (app.py)               │
│  Game UI  ──►  Game Logic (logic_utils.py)             │
│                    │                                    │
│            ┌───────▼──────────────┐                    │
│            │   AI Assistant       │                     │
│            │   (ai_assistant.py)  │                     │
│            │                      │                     │
│            │  1. Observe          │                     │
│            │     (parse state)    │                     │
│            │                      │                     │
│            │  2. Retrieve ──────► RAG System            │
│            │     (TF-IDF)         (rag_system.py)       │
│            │          └─────────► knowledge_base/       │
│            │                      game_strategies.json  │
│            │                                            │
│            │  3. Generate ──────► Claude API            │
│            │     (Haiku)          (anthropic SDK)       │
│            │                                            │
│            │  4. Evaluate ──────► ResponseEvaluator     │
│            │     (quality check)  (evaluator.py)        │
│            │     └── retry once if quality < 0.5        │
│            └──────────────────────────────────────────-┘
│                    │                                    │
│            GameSessionLogger (logger.py)               │
│            writes JSONL to logs/                       │
└───────────────────────────────────────────────────────┘
```

**Data flow:**
1. Player submits a guess → `logic_utils` evaluates it and returns feedback.
2. The app narrows the tracked range (range_low / range_high) based on the feedback.
3. Player clicks **Get AI Hint** → `AIAssistant.get_hint(game_state)` runs the agentic loop.
4. RAG retrieves 3 relevant documents; Claude generates a hint using the context.
5. `ResponseEvaluator` scores the hint; if quality < 0.5, a refined prompt retries automatically.
6. Hint text, confidence %, and quality % are displayed in the UI.
7. All interactions are appended to `logs/sessions_YYYYMMDD.jsonl`.

---

## Setup Instructions

### 1. Clone / open the project

```bash
cd applied-ai-system-project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key

Create a `.env` file in the project root (or export the variable in your shell):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Or in PowerShell:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

### 4. Run the app

```bash
python -m streamlit run app.py
```

The game opens in your browser. The AI assistant panel appears at the bottom. If `ANTHROPIC_API_KEY` is not set, the game still works — only the AI panel is disabled.

### 5. Run tests (no API key needed)

```bash
python -m pytest tests/ -v
```

Expected: **42 tests pass**.

---

## Sample Interactions

### Interaction 1 — Easy difficulty, first guess hint

**Player state:** Easy mode, no guesses yet, range 1–20, 6 attempts remaining.

**Player clicks:** Get AI Hint

**AI response:**
> "Great start! Since this is Easy mode with a range of 1 to 20, your best opening move is to guess **10** — the midpoint. Binary search will let you win in at most 5 guesses. [confidence: 0.9]"

**Displayed metrics:** Confidence: 90% · Quality: 86% · Strategy Present: Yes

---

### Interaction 2 — Normal difficulty, after a "Too High" feedback

**Player state:** Normal mode, guessed 30, got "Too High", range is now 1–29, 6 attempts left.

**Player clicks:** Get AI Hint

**AI response:**
> "You're doing well! Since 30 was too high, your range is now 1–29. The midpoint is 14 — guess that next. Binary search means you only need about 4 more guesses to guarantee a win. [confidence: 0.85]"

**Displayed metrics:** Confidence: 85% · Quality: 100% · Strategy Present: Yes

---

### Interaction 3 — Hard difficulty, 1 attempt left

**Player state:** Hard mode, range narrowed to 61–75, 1 attempt left.

**Player clicks:** Get AI Hint

**AI response:**
> "This is your last attempt — make it count! The midpoint of 61 to 75 is 68. Guess **68** for the best possible chance. Good luck! [confidence: 0.8]"

**Displayed metrics:** Confidence: 80% · Quality: 86% · Strategy Present: Yes

---

### Interaction 4 — Guardrail triggered (evaluator catches secret reveal)

During development, when a test response contained the secret number directly:

**Evaluator output:**
```
guardrails_passed: False
overall_quality: 0.35
```

The response was flagged and logged as a warning. The auto-retry was triggered, producing a guardrail-compliant response.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **TF-IDF RAG (no external vector DB)** | Keeps the project self-contained and reproducible. `chromadb` or `pinecone` would require additional accounts/setup. For a 10-document knowledge base, cosine similarity over manual TF-IDF vectors is sufficient and transparent. |
| **Claude Haiku** | Low latency and cost-effective for short, structured hints. Sonnet would be overkill for 2–4 sentence responses. |
| **Agentic retry loop** | One automatic retry when quality < 0.5 demonstrates genuine agentic behavior without unnecessary API calls. The refined prompt adds the concrete midpoint value, pushing the model toward specific advice. |
| **Guardrails on every response** | The evaluator checks every AI response before displaying it. Blocking secret-number reveals protects game integrity. |
| **JSONL session logging** | Append-only JSONL is simple, human-readable, and easy to analyze post-session without a database. |
| **Graceful AI degradation** | If `ANTHROPIC_API_KEY` is absent or the API call fails, the game continues normally and shows a fallback message. The AI layer is additive, not required. |

---

## Testing Summary

**Total tests: 42 across 3 test files**

| File | Tests | Focus |
|------|-------|-------|
| `tests/test_game_logic.py` | 7 | Core game logic, bug-fix regressions |
| `tests/test_rag_system.py` | 18 | Tokenizer, TF, cosine similarity, retrieval accuracy |
| `tests/test_evaluator.py` | 17 | Strategy detection, guardrails, quality scoring |

**Results:** 42 / 42 passed (0.17 s)

**What worked:** Retrieval accuracy was strong — difficulty-specific queries reliably returned the matching document. Guardrail detection blocked secret-number leakage and "the answer is" phrases reliably.

**What didn't:** The `encouraging_tone` check has a modest false-negative rate because its keyword list is narrow. A response like "Calculate the midpoint." is strategic but scores 0 on tone — slightly penalizing the overall quality score. A semantic classifier would be more accurate but adds complexity not justified here.

**Surprise finding:** The retry mechanism was almost never triggered in manual testing. The model consistently produced high-quality responses on the first attempt, suggesting the evaluation threshold (0.5) is conservative. Raising it to 0.65 in future versions would generate more useful retries.

---

## Reflection and Ethics

### Limitations and biases

The knowledge base is manually curated and encodes a single strategy (binary search). Players who prefer probabilistic or pattern-based approaches receive advice that may not match their style. The TF-IDF retriever also struggles with paraphrased queries — e.g., "what should I guess next?" retrieves weaker results than "strategy midpoint."

### Potential misuse

The AI assistant is low-risk because it operates in a contained game context. The main concern is prompt injection — a user could type adversarial text in the guess input that gets embedded in the hint prompt. Mitigation: the game state dict passed to the AI is built server-side from structured values (difficulty string, integers, feedback string), not raw user input.

### Surprises during testing

The guardrail test `test_guardrail_blocks_secret_number` initially failed because the regex matched partial digit substrings. Fixing it with `\b` word boundaries was straightforward but highlighted how easy it is to build a leaky filter with a naive regex.

### AI collaboration

**Helpful instance:** When designing the agentic retry loop, Claude (Code) suggested passing the computed midpoint explicitly in the refined context string rather than asking the model to compute it again. This made retries reliably more specific and concrete — a non-obvious improvement.

**Flawed instance:** Claude initially suggested using `sklearn.TfidfVectorizer` for the RAG system. While valid, this would have added a heavy dependency for a 10-document knowledge base. After pushing back, the manual TF-IDF implementation was adopted instead — lighter and fully transparent.

---

## File Structure

```
applied-ai-system-project/
├── app.py                          # Streamlit UI + AI panel integration
├── logic_utils.py                  # Pure game logic (range, parse, check, score)
├── ai_assistant.py                 # Agentic workflow (observe→retrieve→generate→evaluate)
├── rag_system.py                   # TF-IDF RAG retrieval
├── evaluator.py                    # Response quality checks + guardrails
├── logger.py                       # Console + file logging, JSONL session log
├── requirements.txt                # Python dependencies
├── knowledge_base/
│   └── game_strategies.json        # 10 RAG knowledge base documents
├── logs/                           # Runtime logs (auto-created)
│   ├── app_YYYYMMDD.log
│   └── sessions_YYYYMMDD.jsonl
└── tests/
    ├── test_game_logic.py          # 7 tests — core game logic
    ├── test_rag_system.py          # 18 tests — RAG components
    └── test_evaluator.py           # 17 tests — evaluator + guardrails
```

---

## Portfolio Reflection

This project demonstrates end-to-end AI system design: a retrieval layer that grounds generation, an agentic loop that self-evaluates and corrects, structured logging for observability, and a guardrail system that keeps the AI's behavior safe and on-topic. It shows that building reliable AI features is as much about evaluation and error-handling as it is about prompting.

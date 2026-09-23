# Hasamex Case Study — Expert Transcript Analyst

An AI-assisted tool that analyzes three expert-call transcripts (France,
Germany, UK — European robotic surgery market) and:

1. Answers a fixed interview guide per expert, with exact quotes and timestamps
2. Verifies every cited quote against the source transcript before showing it
3. Identifies cross-expert themes and disagreements (with citations)
4. Answers free-form questions across all three transcripts, with citations

## Why this design

The core engineering problem in this case is not "call an LLM" — it's
**making sure nothing the LLM says is unverifiable**. So the pipeline is
split into two halves:

- **Deterministic (no LLM):** parsing transcripts into `{turn_id, timestamp,
  speaker, text}` records, and verifying any claimed quote is an exact
  substring of the source turn (whitespace/quote-mark tolerant).
- **LLM-assisted:** reasoning about content (answering guide questions,
  finding themes/disagreements, answering free-form questions) — but every
  quote the LLM cites is checked against the deterministic parser's output
  before it's shown. Unverified quotes are dropped; if all evidence for a
  claim fails verification, the claim itself is marked unverified rather
  than shown.

This means hallucinated or subtly-altered quotes cannot reach the output —
they fail a code-level check, not a "trust the model" check.

## Architecture

data/ Case files (transcripts, interview guide)
backend/
app/
parser.py Deterministic: transcript/guide text -> structured turns
verifier.py Deterministic: quote/turn_id -> verified substring or reject
llm_client.py Thin wrapper around the Groq API (JSON mode, temperature 0)
guide_answers.py LLM: per-expert guide-question answering + verification
themes.py LLM: cross-expert themes/disagreements + verification
qa.py LLM: free-form cross-transcript Q&A + verification
cache.py Caches guide_answers/themes to data/cache/ so repeated
server restarts don't re-spend LLM tokens
main.py FastAPI app exposing all of the above as HTTP endpoints
tests/ pytest suite (parser, verifier, guide answers, themes,
Q&A, API — 40+ tests)


## Tech stack

- **Backend:** FastAPI (Python)
- **LLM:** Groq, `openai/gpt-oss-120b`, temperature 0, JSON mode
- **Verification:** custom whitespace/quote-mark-tolerant substring matcher (no
  external dependency)
- **Tests:** pytest

## Running locally

1. `cd backend`
2. `python -m venv venv`
3. Activate it: `.\venv\Scripts\Activate.ps1` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. `pip install -r requirements.txt`
5. `copy .env.example .env` and put your Groq API key in `.env`
6. `uvicorn app.main:app --reload --port 8000`
7. Open `http://localhost:8000/docs` — every endpoint can be exercised from there.

The first successful startup will call the LLM to precompute guide answers
and themes, and cache the results to `data/cache/`. Subsequent restarts load
from that cache instead of re-calling the LLM.

## API endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Quick liveness check |
| GET | `/api/experts` | List of the three experts |
| GET | `/api/guide` | The interview guide questions |
| GET | `/api/guide-answers` | Every expert × question answer, with verified quotes + timestamps |
| GET | `/api/themes` | Cross-expert themes and disagreements, with verified quotes |
| GET | `/api/transcript/{expert_id}` | Full transcript for one expert (e.g. `E1`) |
| POST | `/api/ask` | `{"question": "..."}` → free-form answer across all transcripts, with citations |

## Testing

```powershell
cd backend
pytest
```

Parser and verifier tests (22 of them) run with no LLM calls. The remaining
tests call the Groq API and are skipped automatically if `GROQ_API_KEY` is
not set.

## Known limitations / what I'd do with more time

- **UI:** Given time constraints, this submission demonstrates the working
  API via the auto-generated Swagger UI (`/docs`) rather than a custom
  frontend. The backend is already structured so a React frontend can call
  these endpoints directly — that would be the next step.
- **Scaling to 30+ transcripts:** the current design loads the full corpus
  into the LLM's context per call, which works for 3 short transcripts but
  won't scale. The next step would be turn-level embeddings in a vector
  store (e.g. ChromaDB), retrieving only the relevant turns per question,
  with the same verification layer applied unchanged — verification is
  decoupled from retrieval by design.
- **LLM variance:** even at temperature 0, Groq's output isn't perfectly
  deterministic between calls. The verification layer exists specifically
  so this doesn't matter for correctness — any output that isn't backed by
  an exact quote is dropped rather than shown.

## Use of AI

I used Claude (Anthropic) throughout this build for planning, code
generation, and debugging (including diagnosing a Groq rate-limit issue
during testing). I reviewed, tested, and understand every part of the
resulting code, and can walk through the design and any file in the
technical interview.
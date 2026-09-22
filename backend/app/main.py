import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.guide_answers import get_all_guide_answers
from app.models import GuideAnswer, InterviewGuide, ThemeItem, Transcript
from app.parser import load_all_transcripts, load_interview_guide
from app.qa import ask_question
from app.themes import get_themes_and_disagreements

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hasamex")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

app = FastAPI(title="Hasamex Transcript Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state, startup pe bharta hai
_state = {
    "transcripts": [],
    "guide": None,
    "guide_answers": [],
    "themes": [],
}


@app.on_event("startup")
def startup() -> None:
    logger.info("Loading transcripts and interview guide...")
    transcripts = load_all_transcripts(DATA_DIR)
    guide = load_interview_guide(DATA_DIR / "Interview_Guide.txt")
    _state["transcripts"] = transcripts
    _state["guide"] = guide

    logger.info("Precomputing guide answers (LLM calls)...")
    guide_answers = get_all_guide_answers(transcripts, guide)
    _state["guide_answers"] = guide_answers

    logger.info("Precomputing themes and disagreements (LLM call)...")
    _state["themes"] = get_themes_and_disagreements(guide_answers, transcripts)

    logger.info("Startup complete: %d transcripts, %d guide answers, %d theme items",
                len(transcripts), len(guide_answers), len(_state["themes"]))


def _get_transcripts() -> List[Transcript]:
    if not _state["transcripts"]:
        raise HTTPException(status_code=503, detail="Server still starting up")
    return _state["transcripts"]


class ExpertSummary(BaseModel):
    expert_id: str
    name: str
    role: str
    market: str
    turn_count: int


class AskRequest(BaseModel):
    question: str


@app.get("/api/health")
def health():
    return {"status": "ok", "experts_loaded": len(_state["transcripts"])}


@app.get("/api/experts", response_model=List[ExpertSummary])
def get_experts():
    return [
        ExpertSummary(
            expert_id=t.expert_id, name=t.name, role=t.role,
            market=t.market, turn_count=len(t.turns),
        )
        for t in _get_transcripts()
    ]


@app.get("/api/guide", response_model=InterviewGuide)
def get_guide():
    if _state["guide"] is None:
        raise HTTPException(status_code=503, detail="Server still starting up")
    return _state["guide"]


@app.get("/api/guide-answers", response_model=List[GuideAnswer])
def get_guide_answers_endpoint():
    return _state["guide_answers"]


@app.get("/api/themes", response_model=List[ThemeItem])
def get_themes_endpoint():
    return _state["themes"]


@app.get("/api/transcript/{expert_id}", response_model=Transcript)
def get_transcript(expert_id: str):
    for transcript in _get_transcripts():
        if transcript.expert_id == expert_id:
            return transcript
    raise HTTPException(status_code=404, detail=f"Expert '{expert_id}' not found")


@app.post("/api/ask")
def ask(request: AskRequest):
    transcripts = _get_transcripts()
    result = ask_question(transcripts, request.question)
    return result
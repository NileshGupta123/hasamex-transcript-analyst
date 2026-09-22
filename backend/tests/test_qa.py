import os
from pathlib import Path

import pytest

from app.parser import load_all_transcripts
from app.qa import ask_question

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY set nahi hai"
)


@pytest.fixture(scope="module")
def transcripts():
    return load_all_transcripts(DATA_DIR)


def test_answerable_question_has_verified_evidence(transcripts):
    result = ask_question(transcripts, "Which expert gave the highest growth estimate, and what number did they give?")
    assert result.status == "answered"
    assert len(result.evidence) > 0
    assert all(e.verified for e in result.evidence)


def test_cross_expert_question_cites_multiple_experts(transcripts):
    result = ask_question(transcripts, "Do all three experts agree that hospital budgets and ROI matter?")
    assert result.status == "answered"
    expert_ids = {e.expert_id for e in result.evidence}
    assert len(expert_ids) >= 2


def test_out_of_scope_question_is_unanswerable(transcripts):
    result = ask_question(transcripts, "What did the experts say about patient satisfaction survey scores?")
    assert result.status == "unanswerable"


def test_empty_question_rejected(transcripts):
    result = ask_question(transcripts, "   ")
    assert result.status == "unanswerable"
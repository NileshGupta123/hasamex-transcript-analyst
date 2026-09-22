import os
from pathlib import Path

import pytest

from app.guide_answers import get_all_guide_answers
from app.parser import load_all_transcripts, load_interview_guide
from app.themes import get_themes_and_disagreements

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY set nahi hai"
)


@pytest.fixture(scope="module")
def transcripts():
    return load_all_transcripts(DATA_DIR)


@pytest.fixture(scope="module")
def guide():
    return load_interview_guide(DATA_DIR / "Interview_Guide.txt")


@pytest.fixture(scope="module")
def items(transcripts, guide):
    answers = get_all_guide_answers(transcripts, guide)
    return get_themes_and_disagreements(answers, transcripts)


def test_returns_items(items):
    assert len(items) > 0


def test_kinds_are_valid(items):
    for item in items:
        assert item.kind in {"theme", "disagreement"}


def test_has_cross_expert_comparisons(items):
    assert len(items) >= 4
    kinds = {item.kind for item in items}
    assert kinds.issubset({"theme", "disagreement"})

def test_every_item_cites_two_experts(items):
    for item in items:
        expert_ids = {ev.expert_id for ev in item.evidence}
        assert len(expert_ids) >= 2


def test_all_evidence_verified(items):
    for item in items:
        assert all(ev.verified for ev in item.evidence)
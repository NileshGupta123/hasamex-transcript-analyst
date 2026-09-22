from pathlib import Path

import pytest

from app.guide_answers import get_all_guide_answers
from app.parser import load_all_transcripts, load_interview_guide
from app.themes import get_themes_and_disagreements

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="session")
def transcripts():
    return load_all_transcripts(DATA_DIR)


@pytest.fixture(scope="session")
def guide():
    return load_interview_guide(DATA_DIR / "Interview_Guide.txt")


@pytest.fixture(scope="session")
def all_guide_answers(transcripts, guide):
    """Poore session me ek hi baar LLM call, sab test files isse reuse karenge."""
    return get_all_guide_answers(transcripts, guide)


@pytest.fixture(scope="session")
def theme_items(transcripts, all_guide_answers):
    """Poore session me ek hi baar LLM call."""
    return get_themes_and_disagreements(all_guide_answers, transcripts)
import os
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY set nahi hai"
)


@pytest.fixture(scope="module")
def e1_answers(all_guide_answers):
    return [a for a in all_guide_answers if a.expert_id == "E1"]


def test_one_answer_per_question(e1_answers, guide):
    assert len(e1_answers) == len(guide.questions)
    assert [a.question_number for a in e1_answers] == [q.number for q in guide.questions]


def test_status_is_valid(e1_answers):
    for answer in e1_answers:
        assert answer.status in {"answered", "not_discussed", "unverified"}


def test_answered_has_verified_evidence(e1_answers):
    for answer in e1_answers:
        if answer.status == "answered":
            assert len(answer.evidence) > 0
            assert all(e.verified for e in answer.evidence)
            assert all(e.expert_id == "E1" for e in answer.evidence)


def test_not_discussed_has_no_evidence(e1_answers):
    for answer in e1_answers:
        if answer.status == "not_discussed":
            assert answer.evidence == []
            assert answer.summary == ""


def test_all_experts(all_guide_answers, transcripts, guide):
    assert len(all_guide_answers) == len(transcripts) * len(guide.questions)
    expert_ids = {a.expert_id for a in all_guide_answers}
    assert expert_ids == {"E1", "E2", "E3"}
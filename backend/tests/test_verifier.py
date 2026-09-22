from pathlib import Path

import pytest

from app.models import Evidence
from app.parser import load_all_transcripts, parse_transcript
from app.verifier import expert_id_from_turn_id, verify_evidence, verify_quote

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="module")
def transcripts():
    return load_all_transcripts(DATA_DIR)


@pytest.fixture(scope="module")
def by_expert(transcripts):
    return {t.expert_id: t for t in transcripts}


def test_exact_match(by_expert):
    e1 = by_expert["E1"]
    quote = e1.get_turn("E1-T02").text[:40]
    result = verify_quote(e1, "E1-T02", quote)
    assert result.verified is True
    assert result.match_start == 0


def test_whitespace_tolerant(by_expert):
    e1 = by_expert["E1"]
    words = e1.get_turn("E1-T02").text.split()[:5]
    quote = "   ".join(words)  # extra spaces daale
    result = verify_quote(e1, "E1-T02", quote)
    assert result.verified is True


def test_wrapped_in_quotes(by_expert):
    e1 = by_expert["E1"]
    snippet = e1.get_turn("E1-T02").text[:30]
    result = verify_quote(e1, "E1-T02", f'"{snippet}"')
    assert result.verified is True


def test_quote_not_present(by_expert):
    e1 = by_expert["E1"]
    result = verify_quote(e1, "E1-T02", "this text is definitely not in the transcript")
    assert result.verified is False
    assert result.reason == "quote_not_found"


def test_turn_not_found(by_expert):
    e1 = by_expert["E1"]
    result = verify_quote(e1, "E1-T99", "anything")
    assert result.verified is False
    assert result.reason == "turn_not_found"


def test_interviewer_turn_rejected(by_expert):
    e1 = by_expert["E1"]
    interviewer_turn = e1.turns[0]
    assert interviewer_turn.is_interviewer
    result = verify_quote(e1, interviewer_turn.turn_id, interviewer_turn.text[:20])
    assert result.verified is False
    assert result.reason == "quote_from_interviewer"


def test_expert_id_from_turn_id():
    assert expert_id_from_turn_id("E1-T02") == "E1"
    assert expert_id_from_turn_id("E12-T07") == "E12"


def test_verify_evidence_across_experts(transcripts, by_expert):
    e1_text = by_expert["E1"].get_turn("E1-T02").text
    e2_text = by_expert["E2"].get_turn("E2-T06").text
    evidence = [
        Evidence(turn_id="E1-T02", quote=e1_text[:25]),
        Evidence(turn_id="E2-T06", quote=e2_text[:25]),
        Evidence(turn_id="E1-T02", quote="not in the transcript at all"),
    ]
    results = verify_evidence(transcripts, evidence)
    assert [r.verified for r in results] == [True, True, False]


def test_verify_evidence_dict_input(transcripts):
    results = verify_evidence(transcripts, [{"turn_id": "E3-T02", "quote": "increasing"}])
    assert results[0].verified is True


def test_curly_quote_normalization():
    raw = (
        "Expert 5 \u2013 Test\nRole: R\nMarket: M\n\n"
        "00:00\nInterviewer: Q?\n\n"
        "00:05\nTest: We\u2019ve seen strong growth.\n"
    )
    transcript = parse_transcript(raw)
    # source me curly apostrophe (\u2019) hai, query me straight ('):
    result = verify_quote(transcript, "E5-T02", "We've seen strong growth")
    assert result.verified is True
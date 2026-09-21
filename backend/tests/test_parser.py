from pathlib import Path

import pytest

from app.parser import (
    load_all_transcripts,
    load_interview_guide,
    parse_transcript,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

SAMPLE = (
    "Expert 9 \u2013 Test Person\r\n"
    "Role: Tester\r\n"
    "Market: Nowhere\r\n"
    "\r\n"
    "00:00\r\n"
    "Interviewer: First question?\r\n"
    "\r\n"
    "00:10\r\n"
    "Test Person: Line one\r\n"
    "continues here.\r\n"
)


@pytest.fixture(scope="module")
def transcripts():
    return load_all_transcripts(DATA_DIR)


def test_loads_three_transcripts(transcripts):
    assert [t.expert_id for t in transcripts] == ["E1", "E2", "E3"]


def test_expert_headers(transcripts):
    e1, e2, e3 = transcripts
    assert (e1.name, e1.market) == ("Dr. Jean Martin", "France")
    assert e1.role == "Head of Urology"
    assert (e2.name, e2.market) == ("Anna Keller", "Germany")
    assert e2.role == "Former Hospital Procurement Director"
    assert (e3.name, e3.market) == ("Dr. Emily Carter", "United Kingdom")
    assert e3.role == "Consultant Urologist"


def test_turn_counts(transcripts):
    for transcript in transcripts:
        assert len(transcript.turns) == 14
        assert len(transcript.expert_turns()) == 7


def test_specific_turn(transcripts):
    e1, e2, _ = transcripts
    turn = e1.get_turn("E1-T02")
    assert turn.timestamp == "00:18"
    assert turn.speaker == "Dr. Martin"
    assert turn.text.startswith("Adoption is growing")

    procurement = e2.get_turn("E2-T06")
    assert procurement.timestamp == "02:08"
    assert "the economic case decides whether it gets approved" in procurement.text


def test_timestamp_seconds(transcripts):
    e1 = transcripts[0]
    assert e1.get_turn("E1-T02").seconds == 18
    assert e1.get_turn("E1-T04").seconds == 80


def test_no_carriage_returns(transcripts):
    for transcript in transcripts:
        for turn in transcript.turns:
            assert "\r" not in turn.text
            assert turn.text == turn.text.strip()


def test_interviewer_flag(transcripts):
    for transcript in transcripts:
        assert transcript.turns[0].is_interviewer is True
        assert transcript.turns[1].is_interviewer is False
        assert all(not t.is_interviewer for t in transcript.expert_turns())


def test_get_turn_unknown_returns_none(transcripts):
    assert transcripts[0].get_turn("E1-T99") is None


def test_guide_parsed():
    guide = load_interview_guide(DATA_DIR / "Interview_Guide.txt")
    assert len(guide.questions) == 6
    assert [q.number for q in guide.questions] == [1, 2, 3, 4, 5, 6]
    assert guide.questions[0].text.startswith("How would you describe current adoption")
    assert "timeline" in guide.questions[5].text
    assert "Europe" in guide.objective


def test_multiline_turn_joined():
    transcript = parse_transcript(SAMPLE)
    assert transcript.expert_id == "E9"
    assert len(transcript.turns) == 2
    assert transcript.turns[1].text == "Line one continues here."


def test_missing_header_raises():
    with pytest.raises(ValueError):
        parse_transcript("00:00\nInterviewer: Hello?\n")


def test_turn_without_speaker_raises():
    raw = "Expert 1 \u2013 X\nRole: R\nMarket: M\n\n00:00\nno speaker label here\n"
    with pytest.raises(ValueError):
        parse_transcript(raw)
import re
from pathlib import Path
from typing import List

from app.models import GuideQuestion, InterviewGuide, Transcript, Turn

TIMESTAMP_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")
HEADER_RE = re.compile(r"^Expert\s+(\d+)\s*[\u2013\u2014-]\s*(.+)$", re.IGNORECASE)
ROLE_RE = re.compile(r"^Role:\s*(.+)$", re.IGNORECASE)
MARKET_RE = re.compile(r"^Market:\s*(.+)$", re.IGNORECASE)
SPEAKER_RE = re.compile(r"^([^:]{1,60}):\s*(.*)$")
QUESTION_RE = re.compile(r"^(\d+)\.\s+(.+)$")


def normalize_newlines(raw: str) -> str:
    """Windows (\\r\\n) aur purane Mac (\\r) line endings ko \\n me badalta hai."""
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def _to_seconds(match) -> int:
    first, second, third = match.groups()
    if third is None:  # MM:SS
        return int(first) * 60 + int(second)
    return int(first) * 3600 + int(second) * 60 + int(third)  # HH:MM:SS


def parse_transcript(raw: str, source_file: str = "") -> Transcript:
    lines = normalize_newlines(raw).split("\n")

    expert_number = None
    name = ""
    role = ""
    market = ""

    raw_turns = []  # har item: {"timestamp", "seconds", "lines"}
    current = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        ts_match = TIMESTAMP_RE.match(stripped)
        if ts_match:
            current = {
                "timestamp": stripped,
                "seconds": _to_seconds(ts_match),
                "lines": [],
            }
            raw_turns.append(current)
            continue

        if current is None:
            # Abhi tak koi timestamp nahi aaya, matlab ye header ka hissa hai
            header = HEADER_RE.match(stripped)
            if header:
                expert_number = int(header.group(1))
                name = header.group(2).strip()
                continue
            role_match = ROLE_RE.match(stripped)
            if role_match:
                role = role_match.group(1).strip()
                continue
            market_match = MARKET_RE.match(stripped)
            if market_match:
                market = market_match.group(1).strip()
                continue
            continue

        # Timestamp ke baad ki line, isi turn ka text hai (multi-line ho sakta hai)
        current["lines"].append(stripped)

    if expert_number is None:
        raise ValueError("Header line nahi mili (expected: 'Expert <number> - <name>')")
    if not raw_turns:
        raise ValueError("Transcript me koi timestamp/turn nahi mila")

    expert_id = f"E{expert_number}"
    turns: List[Turn] = []

    for index, item in enumerate(raw_turns, start=1):
        body = " ".join(item["lines"])
        speaker_match = SPEAKER_RE.match(body)
        if not speaker_match:
            raise ValueError(
                f"Turn at {item['timestamp']} me 'Speaker: text' format nahi mila"
            )
        speaker = speaker_match.group(1).strip()
        text = speaker_match.group(2).strip()
        turns.append(
            Turn(
                turn_id=f"{expert_id}-T{index:02d}",
                expert_id=expert_id,
                index=index,
                timestamp=item["timestamp"],
                seconds=item["seconds"],
                speaker=speaker,
                is_interviewer=speaker.lower().startswith("interviewer"),
                text=text,
            )
        )

    return Transcript(
        expert_id=expert_id,
        expert_number=expert_number,
        name=name,
        role=role,
        market=market,
        source_file=source_file,
        turns=turns,
    )


def load_transcript(path: Path) -> Transcript:
    path = Path(path)
    raw = path.read_text(encoding="utf-8-sig")  # BOM ho toh hata deta hai
    return parse_transcript(raw, source_file=path.name)


def load_all_transcripts(data_dir: Path) -> List[Transcript]:
    files = sorted(Path(data_dir).glob("Transcript_*.txt"))
    if not files:
        raise FileNotFoundError(f"{data_dir} me Transcript_*.txt files nahi mili")

    transcripts = [load_transcript(f) for f in files]
    transcripts.sort(key=lambda t: t.expert_number)

    ids = [t.expert_id for t in transcripts]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate expert IDs mile: {ids}")
    return transcripts


def parse_interview_guide(raw: str) -> InterviewGuide:
    lines = [line.strip() for line in normalize_newlines(raw).split("\n")]

    title = ""
    objective_lines: List[str] = []
    questions: List[GuideQuestion] = []
    section = None

    for line in lines:
        if not line:
            continue
        if not title:
            title = line
            continue

        lowered = line.lower()
        if lowered.startswith("project objective"):
            section = "objective"
            remainder = line.split(":", 1)[1].strip() if ":" in line else ""
            if remainder:
                objective_lines.append(remainder)
            continue
        if lowered.startswith("questions"):
            section = "questions"
            continue

        if section == "objective":
            objective_lines.append(line)
        elif section == "questions":
            match = QUESTION_RE.match(line)
            if match:
                questions.append(
                    GuideQuestion(number=int(match.group(1)), text=match.group(2).strip())
                )

    if not questions:
        raise ValueError("Interview guide me numbered questions nahi mile")

    return InterviewGuide(
        title=title,
        objective=" ".join(objective_lines),
        questions=questions,
    )


def load_interview_guide(path: Path) -> InterviewGuide:
    raw = Path(path).read_text(encoding="utf-8-sig")
    return parse_interview_guide(raw)


if __name__ == "__main__":
    # Quick check: backend folder se chalao -> python -m app.parser
    data_dir = Path(__file__).resolve().parents[2] / "data"

    for transcript in load_all_transcripts(data_dir):
        print(
            f"{transcript.expert_id} | {transcript.name} | {transcript.role} | "
            f"{transcript.market} | {len(transcript.turns)} turns "
            f"({len(transcript.expert_turns())} expert)"
        )
        first = transcript.expert_turns()[0]
        print(f"   {first.turn_id} [{first.timestamp}] {first.speaker}: {first.text[:80]}...")

    guide = load_interview_guide(data_dir / "Interview_Guide.txt")
    print(f"\nGuide: {len(guide.questions)} questions")
    for question in guide.questions:
        print(f"   Q{question.number}. {question.text}")
from typing import List

from app.llm_client import call_json
from app.models import Evidence, QAResult, Transcript
from app.verifier import verify_evidence

SYSTEM_PROMPT = """You answer free-form questions using THREE expert-call
transcripts about the European robotic surgery market.

Rules:
- Answer ONLY using the transcripts provided. Never use outside knowledge.
- If the transcripts do not contain enough information to answer the
  question, set status to "unanswerable" and explain briefly in "answer"
  why (e.g. "None of the experts discuss X").
- Every factual claim in your answer must be backed by at least one piece
  of evidence (turn_id + exact quote).
- Every quote you cite MUST be an exact, verbatim substring copied from the
  transcript text for that turn_id. Do not paraphrase inside a quote. Do not
  merge words from two different turns into one quote.
- When a claim involves a specific number, percentage, or timeframe, the
  cited quote must include that number/percentage/timeframe verbatim.
- If the question asks to compare experts, be precise about which expert
  said what, and preserve any scope qualifiers they used (e.g. "in stronger
  centres" vs "across the whole market") rather than generalizing.
- Keep the answer concise: 2-5 sentences.

Respond ONLY with a JSON object of this exact shape, nothing else:
{
  "status": "answered" | "unanswerable",
  "answer": "<string>",
  "evidence": [{"turn_id": "<string>", "quote": "<string>"}]
}"""


def _build_user_prompt(transcripts: List[Transcript], question: str) -> str:
    lines = ["TRANSCRIPTS:"]
    for transcript in transcripts:
        lines.append(f"\n--- {transcript.expert_id}: {transcript.name} ({transcript.role}, {transcript.market}) ---")
        for turn in transcript.turns:
            lines.append(f"[{turn.turn_id} | {turn.timestamp}] {turn.speaker}: {turn.text}")

    lines.append(f"\nQUESTION: {question}")
    return "\n".join(lines)


def ask_question(transcripts: List[Transcript], question: str) -> QAResult:
    question = question.strip()
    if not question:
        return QAResult(question=question, status="unanswerable", answer="Please ask a non-empty question.", evidence=[])

    user_prompt = _build_user_prompt(transcripts, question)
    raw = call_json(SYSTEM_PROMPT, user_prompt)

    status = raw.get("status", "unanswerable")
    answer = raw.get("answer", "") or ""
    raw_evidence = raw.get("evidence", []) or []

    if status != "answered" or not raw_evidence:
        return QAResult(question=question, status="unanswerable", answer=answer, evidence=[])

    evidence_items = [
        Evidence(turn_id=e.get("turn_id", ""), quote=e.get("quote", ""))
        for e in raw_evidence
    ]
    verified_results = verify_evidence(transcripts, evidence_items)
    verified_only = [r for r in verified_results if r.verified]

    if not verified_only:
        return QAResult(
            question=question, status="unanswerable",
            answer="The model's answer could not be verified against the transcripts.",
            evidence=verified_results,  # debugging ke liye
        )

    return QAResult(question=question, status="answered", answer=answer, evidence=verified_only)


if __name__ == "__main__":
    from pathlib import Path

    from app.parser import load_all_transcripts

    data_dir = Path(__file__).resolve().parents[2] / "data"
    transcripts = load_all_transcripts(data_dir)

    questions = [
        "Which expert is most optimistic about future growth, and why?",
        "Do all three experts agree that ROI is the deciding factor?",
        "What did the experts say about patient satisfaction surveys?",  # transcripts me nahi hai
    ]

    for q in questions:
        result = ask_question(transcripts, q)
        print(f"\nQ: {result.question}")
        print(f"[{result.status}] {result.answer}")
        for ev in result.evidence:
            print(f"   -> {ev.expert_id} {ev.turn_id} [{ev.timestamp}]: \"{ev.quote}\"")
from typing import List

from app.llm_client import call_json
from app.models import Evidence, GuideAnswer, InterviewGuide, Transcript
from app.verifier import verify_evidence

SYSTEM_PROMPT = """You are analyzing ONE expert-call transcript to answer a fixed interview guide.

Rules:
- Answer ONLY using this transcript. Never use outside knowledge.
- For each question, decide if the expert explicitly addressed it.
  - If yes: write a 1-2 sentence summary in your own words, and cite the
    exact turn_id(s) and exact quote(s) from the transcript that support it.
  - If the expert did not explicitly address a question: set status to
    "not_discussed", summary to "", and evidence to an empty list. Do NOT
    guess or infer an answer that was not stated.
- Every quote you cite MUST be an exact, verbatim substring copied from the
  transcript text for that turn_id. Do not paraphrase inside a quote. Do not
  combine words from two different turns into one quote.
- Quotes should be meaningful (at least 6 words) and self-contained, not a
  single word or an ambiguous sentence fragment.
- A question can have more than one supporting turn_id/quote if the answer
  is spread across multiple turns.

Respond ONLY with a JSON object of this exact shape, nothing else:
{
  "answers": [
    {
      "question_number": <int>,
      "status": "answered" | "not_discussed",
      "summary": "<string, empty if not_discussed>",
      "evidence": [{"turn_id": "<string>", "quote": "<string>"}]
    }
  ]
}
One entry per question number, in order."""


def _build_user_prompt(transcript: Transcript, guide: InterviewGuide) -> str:
    lines = [f"EXPERT: {transcript.name} ({transcript.role}, {transcript.market})", "", "TRANSCRIPT:"]
    for turn in transcript.turns:
        lines.append(f"[{turn.turn_id} | {turn.timestamp}] {turn.speaker}: {turn.text}")

    lines.append("")
    lines.append("INTERVIEW GUIDE QUESTIONS:")
    for question in guide.questions:
        lines.append(f"{question.number}. {question.text}")

    return "\n".join(lines)


def get_guide_answers(transcript: Transcript, guide: InterviewGuide) -> List[GuideAnswer]:
    user_prompt = _build_user_prompt(transcript, guide)
    raw = call_json(SYSTEM_PROMPT, user_prompt)

    raw_answers = raw.get("answers", [])
    by_number = {a.get("question_number"): a for a in raw_answers}

    results: List[GuideAnswer] = []
    for question in guide.questions:
        item = by_number.get(question.number, {})
        status = item.get("status", "not_discussed")
        summary = item.get("summary", "") or ""
        raw_evidence = item.get("evidence", []) or []

        if status != "answered" or not raw_evidence:
            results.append(
                GuideAnswer(
                    question_number=question.number,
                    expert_id=transcript.expert_id,
                    status="not_discussed",
                    summary="",
                    evidence=[],
                )
            )
            continue

        evidence_items = [
            Evidence(turn_id=e.get("turn_id", ""), quote=e.get("quote", ""))
            for e in raw_evidence
        ]
        verified_results = verify_evidence([transcript], evidence_items)
        verified_only = [r for r in verified_results if r.verified]

        if not verified_only:
            results.append(
                GuideAnswer(
                    question_number=question.number,
                    expert_id=transcript.expert_id,
                    status="unverified",
                    summary=summary,
                    evidence=verified_results,  # debugging ke liye failed evidence rakhte hain
                )
            )
            continue

        results.append(
            GuideAnswer(
                question_number=question.number,
                expert_id=transcript.expert_id,
                status="answered",
                summary=summary,
                evidence=verified_only,
            )
        )

    return results


def get_all_guide_answers(transcripts: List[Transcript], guide: InterviewGuide) -> List[GuideAnswer]:
    all_answers: List[GuideAnswer] = []
    for transcript in transcripts:
        all_answers.extend(get_guide_answers(transcript, guide))
    return all_answers


if __name__ == "__main__":
    from pathlib import Path

    from app.parser import load_all_transcripts, load_interview_guide

    data_dir = Path(__file__).resolve().parents[2] / "data"
    transcripts = load_all_transcripts(data_dir)
    guide = load_interview_guide(data_dir / "Interview_Guide.txt")

    answers = get_all_guide_answers(transcripts, guide)
    for answer in answers:
        print(f"\n{answer.expert_id} Q{answer.question_number} [{answer.status}]")
        if answer.summary:
            print(f"   {answer.summary}")
        for ev in answer.evidence:
            print(f"   -> {ev.turn_id} [{ev.timestamp}] \"{ev.quote}\"")
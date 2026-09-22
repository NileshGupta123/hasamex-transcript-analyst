from typing import List

from app.guide_answers import GuideAnswer
from app.llm_client import call_json
from app.models import Evidence, ThemeItem, Transcript
from app.verifier import verify_evidence

SYSTEM_PROMPT = """You are comparing verified answers from THREE expert-call
transcripts about the same interview guide, to find cross-expert themes and
disagreements.

You will be given, for each guide question, each expert's verified summary
and the exact quotes that support it. Only use this material - do not
introduce outside knowledge, and do not use any expert's transcript directly.

Task:
1. Identify THEMES: points where two or more experts substantively agree.
2. Identify DISAGREEMENTS: points where experts give conflicting views,
   numbers, or emphasis. A disagreement can also be a case where the
   interviewer suggested something and one expert explicitly rejected it.

Rules:
- Every theme/disagreement must cite evidence from at least 2 different
  experts (2 different expert_id values), using their turn_id.
- Every quote you cite MUST be an exact, verbatim substring copied from the
  provided material for that turn_id. Do not paraphrase inside a quote.
- Preserve scope qualifiers precisely. If one expert says a number applies
  "in stronger centres" and another says "across the whole market", treat
  these as different claims, not the same claim - do not generalize away
  the qualifier in your title or summary.
- Do not invent a disagreement that is not clearly present in the material.
- When a theme or disagreement involves a specific number, percentage, or
  timeframe stated by an expert, the cited quote for that expert MUST
  include that number/percentage/timeframe verbatim, not just a qualitative
  sentence around it.
- Prefer 3-6 themes and 2-4 disagreements, whichever are genuinely supported.

Respond ONLY with a JSON object of this exact shape, nothing else:
{
  "themes": [
    {"title": "<short string>", "summary": "<1-3 sentences>",
     "evidence": [{"turn_id": "<string>", "quote": "<string>"}]}
  ],
  "disagreements": [
    {"title": "<short string>", "summary": "<1-3 sentences>",
     "evidence": [{"turn_id": "<string>", "quote": "<string>"}]}
  ]
}"""


def _build_user_prompt(answers: List[GuideAnswer], transcripts: List[Transcript]) -> str:
    names = {t.expert_id: f"{t.name} ({t.market})" for t in transcripts}
    by_question: dict = {}
    for answer in answers:
        by_question.setdefault(answer.question_number, []).append(answer)

    lines = ["VERIFIED MATERIAL BY QUESTION:"]
    for question_number in sorted(by_question):
        lines.append(f"\nQuestion {question_number}:")
        for answer in by_question[question_number]:
            label = names.get(answer.expert_id, answer.expert_id)
            if answer.status != "answered":
                lines.append(f"  {answer.expert_id} ({label}): not discussed")
                continue
            lines.append(f"  {answer.expert_id} ({label}): {answer.summary}")
            for ev in answer.evidence:
                lines.append(f"    -> {ev.turn_id} [{ev.timestamp}]: \"{ev.quote}\"")

    return "\n".join(lines)


def _parse_items(raw_items: list, kind: str, transcripts: List[Transcript]) -> List[ThemeItem]:
    results: List[ThemeItem] = []
    for item in raw_items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        raw_evidence = item.get("evidence", []) or []
        if not title or not raw_evidence:
            continue

        evidence_items = [
            Evidence(turn_id=e.get("turn_id", ""), quote=e.get("quote", ""))
            for e in raw_evidence
        ]
        verified_results = verify_evidence(transcripts, evidence_items)
        verified_only = [r for r in verified_results if r.verified]

        # Kam se kam 2 alag experts se verified evidence chahiye
        expert_ids = {r.expert_id for r in verified_only}
        if len(expert_ids) < 2:
            continue

        results.append(
            ThemeItem(kind=kind, title=title, summary=summary, evidence=verified_only)
        )
    return results


def get_themes_and_disagreements(
    answers: List[GuideAnswer], transcripts: List[Transcript]
) -> List[ThemeItem]:
    user_prompt = _build_user_prompt(answers, transcripts)
    raw = call_json(SYSTEM_PROMPT, user_prompt)

    themes = _parse_items(raw.get("themes", []), "theme", transcripts)
    disagreements = _parse_items(raw.get("disagreements", []), "disagreement", transcripts)
    return themes + disagreements


if __name__ == "__main__":
    from pathlib import Path

    from app.guide_answers import get_all_guide_answers
    from app.parser import load_all_transcripts, load_interview_guide

    data_dir = Path(__file__).resolve().parents[2] / "data"
    transcripts = load_all_transcripts(data_dir)
    guide = load_interview_guide(data_dir / "Interview_Guide.txt")

    answers = get_all_guide_answers(transcripts, guide)
    items = get_themes_and_disagreements(answers, transcripts)

    for item in items:
        print(f"\n[{item.kind.upper()}] {item.title}")
        print(f"   {item.summary}")
        for ev in item.evidence:
            print(f"   -> {ev.expert_id} {ev.turn_id} [{ev.timestamp}]: \"{ev.quote}\"")
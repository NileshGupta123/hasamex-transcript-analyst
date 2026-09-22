import re
from typing import Dict, List, Sequence, Union

from app.models import Evidence, Transcript, VerificationResult

_CHAR_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'",   # curly single quotes -> straight
    "\u201c": '"', "\u201d": '"',   # curly double quotes -> straight
    "\u2013": "-", "\u2014": "-",   # en/em dash -> hyphen
    "\u00a0": " ",                  # non-breaking space -> normal space
})

_WRAP_PAIRS = [('"', '"'), ("'", "'"), ("\u201c", "\u201d"), ("\u2018", "\u2019")]


def normalize_chars(text: str) -> str:
    """Curly quotes/dashes ko straight me badalta hai. Har replacement
    single-char-for-single-char hai, isliye string ki length nahi badalti
    aur match ke offsets original text pe bhi valid rehte hain."""
    return text.translate(_CHAR_MAP)


def _strip_wrapping_quotes(text: str) -> str:
    text = text.strip()
    for left, right in _WRAP_PAIRS:
        if len(text) >= 2 and text[0] == left and text[-1] == right:
            return text[1:-1].strip()
    return text


def expert_id_from_turn_id(turn_id: str) -> str:
    return turn_id.split("-T")[0]


def verify_quote(transcript: Transcript, turn_id: str, quote: str) -> VerificationResult:
    """Check karta hai ki `quote`, transcript ke `turn_id` wale turn ka
    (whitespace/curly-quote farak chhodkar) exact substring hai ya nahi."""
    expert_id = expert_id_from_turn_id(turn_id)
    turn = transcript.get_turn(turn_id)

    if turn is None:
        return VerificationResult(
            turn_id=turn_id, expert_id=expert_id, verified=False,
            quote=quote, reason="turn_not_found",
        )

    if turn.is_interviewer:
        return VerificationResult(
            turn_id=turn_id, expert_id=expert_id, verified=False,
            quote=quote, timestamp=turn.timestamp, speaker=turn.speaker,
            reason="quote_from_interviewer",
        )

    cleaned_quote = _strip_wrapping_quotes(quote)
    if not cleaned_quote:
        return VerificationResult(
            turn_id=turn_id, expert_id=expert_id, verified=False,
            quote=quote, timestamp=turn.timestamp, speaker=turn.speaker,
            reason="empty_quote",
        )

    norm_turn_text = normalize_chars(turn.text)
    norm_quote = normalize_chars(cleaned_quote)
    tokens = norm_quote.split()
    pattern = r"\s+".join(re.escape(token) for token in tokens)

    match = re.search(pattern, norm_turn_text)
    if not match:
        return VerificationResult(
            turn_id=turn_id, expert_id=expert_id, verified=False,
            quote=quote, timestamp=turn.timestamp, speaker=turn.speaker,
            reason="quote_not_found",
        )

    return VerificationResult(
        turn_id=turn_id, expert_id=expert_id, verified=True,
        quote=turn.text[match.start():match.end()],  # asli transcript text, LLM ka nahi
        timestamp=turn.timestamp, speaker=turn.speaker,
        match_start=match.start(), match_end=match.end(),
    )


def verify_evidence(
    transcripts: Union[Sequence[Transcript], Dict[str, Transcript]],
    evidence: Sequence[Union[Evidence, dict]],
) -> List[VerificationResult]:
    """Evidence items (turn_id + quote) ki poori list verify karta hai,
    multiple transcripts ke across (turn_id ke prefix se expert dhundh leta hai)."""
    if isinstance(transcripts, dict):
        by_expert = transcripts
    else:
        by_expert = {t.expert_id: t for t in transcripts}

    results: List[VerificationResult] = []
    for item in evidence:
        if isinstance(item, dict):
            turn_id = item.get("turn_id", "")
            quote = item.get("quote", "")
        else:
            turn_id, quote = item.turn_id, item.quote

        expert_id = expert_id_from_turn_id(turn_id)
        transcript = by_expert.get(expert_id)
        if transcript is None:
            results.append(
                VerificationResult(
                    turn_id=turn_id, expert_id=expert_id, verified=False,
                    quote=quote, reason="expert_not_found",
                )
            )
            continue
        results.append(verify_quote(transcript, turn_id, quote))

    return results
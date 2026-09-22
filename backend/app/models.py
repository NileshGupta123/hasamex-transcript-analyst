from typing import List, Optional

from pydantic import BaseModel


class Turn(BaseModel):
    turn_id: str          # jaise "E1-T02"
    expert_id: str        # jaise "E1"
    index: int            # transcript me turn ka number (1 se shuru)
    timestamp: str        # jaise "02:08", file se as-is
    seconds: int          # sorting ke liye, 02:08 -> 128
    speaker: str          # jaise "Dr. Martin" ya "Interviewer"
    is_interviewer: bool
    text: str


class Transcript(BaseModel):
    expert_id: str
    expert_number: int
    name: str
    role: str
    market: str
    source_file: str
    turns: List[Turn]

    def get_turn(self, turn_id: str) -> Optional[Turn]:
        for turn in self.turns:
            if turn.turn_id == turn_id:
                return turn
        return None

    def expert_turns(self) -> List[Turn]:
        """Sirf expert ke turns (interviewer ke nahi). Quotes yahin se aayenge."""
        return [turn for turn in self.turns if not turn.is_interviewer]


class GuideQuestion(BaseModel):
    number: int
    text: str


class InterviewGuide(BaseModel):
    title: str
    objective: str
    questions: List[GuideQuestion]


class Evidence(BaseModel):
    """LLM ka claim: is turn me ye quote hai. Verify hone se pehle isse
    'unverified evidence' maano."""
    turn_id: str
    quote: str


class VerificationResult(BaseModel):
    """Evidence ko transcript ke against check karne ka result."""
    turn_id: str
    expert_id: str
    verified: bool
    quote: str                      # verified=True toh original transcript text, warna LLM ka claim
    timestamp: Optional[str] = None
    speaker: Optional[str] = None
    reason: Optional[str] = None    # verified=False hone ki wajah
    match_start: Optional[int] = None
    match_end: Optional[int] = None
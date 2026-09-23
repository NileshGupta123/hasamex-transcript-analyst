import json
from pathlib import Path
from typing import List

from app.models import GuideAnswer, ThemeItem

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
GUIDE_ANSWERS_CACHE = CACHE_DIR / "guide_answers.json"
THEMES_CACHE = CACHE_DIR / "themes.json"


def save_guide_answers(answers: List[GuideAnswer]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = [a.model_dump() for a in answers]
    GUIDE_ANSWERS_CACHE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_guide_answers() -> List[GuideAnswer]:
    data = json.loads(GUIDE_ANSWERS_CACHE.read_text(encoding="utf-8"))
    return [GuideAnswer.model_validate(item) for item in data]


def guide_answers_cached() -> bool:
    return GUIDE_ANSWERS_CACHE.exists()


def save_themes(items: List[ThemeItem]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = [t.model_dump() for t in items]
    THEMES_CACHE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_themes() -> List[ThemeItem]:
    data = json.loads(THEMES_CACHE.read_text(encoding="utf-8"))
    return [ThemeItem.model_validate(item) for item in data]


def themes_cached() -> bool:
    return THEMES_CACHE.exists()
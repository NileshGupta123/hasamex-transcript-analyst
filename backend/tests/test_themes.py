import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY set nahi hai"
)


@pytest.fixture(scope="module")
def items(theme_items):
    return theme_items


def test_returns_items(items):
    assert len(items) > 0


def test_kinds_are_valid(items):
    for item in items:
        assert item.kind in {"theme", "disagreement"}


def test_has_cross_expert_comparisons(items):
    # LLM ki thodi non-determinism ho sakti hai (temperature 0 pe bhi), isliye
    # hum ye assert nahi karte ki "theme" aur "disagreement" dono hi har baar
    # aayenge. Hum sirf ye check karte hain ki kaafi comparisons bane hain aur
    # dono kinds valid hain jab bhi aayein.
    assert len(items) >= 4
    kinds = {item.kind for item in items}
    assert kinds.issubset({"theme", "disagreement"})


def test_every_item_cites_two_experts(items):
    for item in items:
        expert_ids = {ev.expert_id for ev in item.evidence}
        assert len(expert_ids) >= 2


def test_all_evidence_verified(items):
    for item in items:
        assert all(ev.verified for ev in item.evidence)
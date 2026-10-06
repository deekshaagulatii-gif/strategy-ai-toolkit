import json
from pathlib import Path

from toolkit import tender

TENDER = Path("data/sample_tender.txt").read_text()
DRAFT = Path("data/sample_draft.txt").read_text()


def reply(**overrides):
    criteria = [
        {"ref": "M1", "criterion": "GDPR compliance", "type": "mandatory", "weight": None, "rating": "missing",
         "evidence": [], "gap": "No data protection statement.", "fix": "Add one."},
        {"ref": "B", "criterion": "Methodology", "type": "scored", "weight": 30, "rating": "well",
         "evidence": ["Each phase ends with a steering group review."], "gap": "", "fix": ""},
        {"ref": "C", "criterion": "Stakeholder engagement", "type": "scored", "weight": 15, "rating": "brief",
         "evidence": ["We will also interview partner organisations."], "gap": "No seldom-heard groups.", "fix": "Add."},
        {"ref": "D", "criterion": "Innovation and creativity", "type": "scored", "weight": 15, "rating": "brief",
         "evidence": ["We use AI-powered sentiment analysis."], "gap": "Vague.", "fix": "Name the method."},
        {"ref": "F", "criterion": "Price", "type": "price", "weight": 15, "rating": "well", "evidence": []},
    ]
    for c in criteria:
        c.update(overrides.get(c["ref"], {}))
    return json.dumps({"criteria": criteria})


def test_quote_not_in_draft_is_not_trusted(fake_llm):
    result = tender.check(TENDER, DRAFT, fake_llm(reply()))
    d = next(c for c in result["criteria"] if c["ref"] == "D")
    assert d["rating"] == "unverified" and d["not_found"]


def test_invented_weight_is_flagged(fake_llm):
    result = tender.check(TENDER, DRAFT, fake_llm(reply(B={"weight": 40})))
    assert any("40%" in w for w in result["warnings"])


def test_coverage_and_priorities(fake_llm):
    result = tender.check(TENDER, DRAFT, fake_llm(reply()))
    # B well (30) + C brief (7.5) + D unverified (0) out of 60 scored marks
    assert result["coverage"] == round(100 * 37.5 / 60)
    assert result["priorities"][0]["ref"] == "M1"          # mandatory gap first
    assert result["priorities"][1]["ref"] == "D"           # then most marks at risk
    assert next(c for c in result["criteria"] if c["ref"] == "F")["rating"] == "not_assessed"


def test_markdown_warns_about_disqualification(fake_llm):
    md = tender.to_markdown(tender.check(TENDER, DRAFT, fake_llm(reply())))
    assert "risk of disqualification" in md and "not a predicted score" in md

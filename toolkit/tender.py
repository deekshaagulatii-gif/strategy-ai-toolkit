"""Tender Fit Checker: checks a draft tender response against the tender's own scored criteria before submission.

The AI reads the tender, lists each mandatory requirement and scored criterion with its weight, and rates how well the
draft addresses it, quoting the draft as evidence. The code then checks the AI's work:

- every evidence quote must appear word for word in the draft, or the rating is not trusted;
- every weight must appear in the tender text, so no weight is invented;
- weights must add up to 100%.

The output is a gap list ordered by marks at risk. It is a review aid, not a predicted score.
"""
from __future__ import annotations

import re

from .llm import LLM, parse_json
from .text import normalise

RATINGS = {"well": "Addressed well", "brief": "Mentioned briefly", "missing": "Missing",
           "unverified": "Evidence not found in draft", "not_assessed": "Assessed separately"}
SCORE = {"well": 1.0, "brief": 0.5}

PROMPT = """You are a bid reviewer checking a DRAFT tender response before submission.

TENDER:
<<<
{tender}
>>>

DRAFT RESPONSE:
<<<
{draft}
>>>

1. List every mandatory (pass/fail) requirement and every scored award criterion that the TENDER states. Use the
   tender's own reference (e.g. "M1", "B") and its stated weight as a number. Never invent a criterion or a weight;
   use null if no weight is stated. Price, or anything assessed outside the written response, has type "price".
2. Rate how well the DRAFT addresses each one: "well" (specific and complete), "brief" (mentioned but thin or
   generic), "missing" (not addressed). Use "not_assessed" for type "price".
3. Evidence: copy up to 2 sentences from the DRAFT, word for word, that support the rating. Empty if missing.
4. Gap: what an evaluator would mark down. Fix: one concrete addition. Do not invent facts about the bidder.

Return ONLY JSON:
{{"criteria":[{{"ref":"","criterion":"","type":"mandatory|scored|price","weight":null,"looking_for":"",
"rating":"well|brief|missing|not_assessed","evidence":[""],"gap":"","fix":""}}]}}"""


def check(tender: str, draft: str, llm: LLM) -> dict:
    if not tender.strip() or not draft.strip():
        raise ValueError("Both the tender text and the draft response are needed.")
    raw = parse_json(llm.complete(PROMPT.format(tender=tender, draft=draft), max_tokens=4000))
    return verify(raw, tender, draft)


def verify(result: dict, tender: str, draft: str) -> dict:
    """Checks the AI's output against the source texts and adds coverage, priorities and warnings."""
    draft_n, warnings = normalise(draft), []
    criteria = result.get("criteria", [])
    for c in criteria:
        c["verified"] = [q for q in c.get("evidence", []) if q and normalise(q) and normalise(q) in draft_n]
        c["not_found"] = [q for q in c.get("evidence", []) if q and q not in c["verified"]]
        if c.get("type") == "price":
            c["rating"] = "not_assessed"
        elif c.get("rating") in SCORE and not c["verified"]:
            c["rating"] = "unverified"
        w = c.get("weight")
        c["weight_found"] = w is None or bool(re.search(rf"(?<!\d){re.escape(str(w))}\s*%", tender))
        if not c["weight_found"]:
            warnings.append(f"{c.get('ref', '?')}: weight {w}% does not appear in the tender. Check it.")

    weighted = [c for c in criteria if c.get("type") in ("scored", "price") and isinstance(c.get("weight"), (int, float))]
    total = sum(c["weight"] for c in weighted)
    if weighted and abs(total - 100) > 0.5:
        warnings.append(f"Weights add up to {total:g}%, not 100%. A criterion may have been missed.")

    scored = [c for c in weighted if c.get("type") == "scored"]
    possible = sum(c["weight"] for c in scored)
    secured = sum(c["weight"] * SCORE.get(c.get("rating"), 0) for c in scored)
    mandatory_gaps = [c for c in criteria if c.get("type") == "mandatory" and c.get("rating") not in SCORE]
    at_risk = sorted((c for c in scored if c.get("rating") != "well"),
                     key=lambda c: c["weight"] * (1 - SCORE.get(c.get("rating"), 0)), reverse=True)

    result.update(
        coverage=round(100 * secured / possible) if possible else None,
        priorities=mandatory_gaps + at_risk,
        warnings=warnings,
    )
    return result


def to_markdown(result: dict) -> str:
    out = ["# Tender fit check", ""]
    if result.get("coverage") is not None:
        out += [f"**Weighted coverage of the scored criteria: {result['coverage']}%** "
                "(a rough guide to gaps, not a predicted score).", ""]
    for w in result.get("warnings", []):
        out.append(f"> WARNING: {w}")
    out += ["", "| Ref | Criterion | Type | Weight | Rating | Evidence from draft |", "| --- | --- | --- | --- | --- | --- |"]
    for c in result.get("criteria", []):
        weight = f"{c['weight']:g}%" if isinstance(c.get("weight"), (int, float)) else "-"
        ev = " / ".join(f'"{q}"' for q in c.get("verified", [])) or "-"
        out.append(f"| {c.get('ref', '')} | {c.get('criterion', '')} | {c.get('type', '')} | {weight} | "
                   f"{RATINGS.get(c.get('rating'), c.get('rating'))} | {ev} |")
    if result.get("priorities"):
        out += ["", "## Fix before submission, in order of marks at risk", ""]
        for c in result["priorities"]:
            tag = "MANDATORY: risk of disqualification. " if c.get("type") == "mandatory" else ""
            out.append(f"1. **{c.get('ref', '')} {c.get('criterion', '')}**: {tag}{c.get('gap', '')} Fix: {c.get('fix', '')}")
    out += ["", "_AI first review. A bid manager checks every rating before submission._"]
    return "\n".join(out)

"""Outcome Tracker: helps a client move from counting outputs to measuring outcomes after a strategy launches.

Step 1 (analyse): AI sorts a plan's actions into outputs (work done) and outcomes (change for people) and proposes
indicators. The code checks that every action was classified exactly once and that each indicator has a data source
and a reporting frequency.

Step 2 (draft_update): AI drafts a progress update for the board, staff or the public from the action statuses.
The code flags any number in the draft that does not appear in the inputs, because the update must never invent figures.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .llm import LLM, parse_json

STATUSES = ["On track", "At risk", "Behind", "Not started", "Complete"]
AUDIENCES = {
    "board": "Audience: the Board. Under 180 words. Overall status in one line, then risks and decisions needed, then highlights.",
    "staff": "Audience: staff. Under 200 words. What progress means for their day-to-day work and where help is needed.",
    "public": "Audience: the public. Under 180 words. Plain English, no unexplained acronyms, focus on what changes for people.",
}


def load_outcomes(path: str | Path = "data/hiqa_outcomes.json") -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["outcomes"]


ANALYSE_PROMPT = """You are helping a strategy consultant apply an "outcomes, not outputs" lens to a public-sector plan.

Outcome: "{name}"
Planned actions:
{actions}

1. Classify EVERY action by its number as "output" (an activity or deliverable the organisation produces) or "outcome"
   (it directly describes or measures a change for people). Most plan actions are outputs; be strict. One plain sentence why.
2. Propose 3 or 4 indicators showing whether the outcome is really happening for people. For each: indicator, what it
   shows, a realistic data source, and a reporting frequency.
3. One sentence naming the biggest measurement gap.

Return ONLY JSON:
{{"actions":[{{"number":1,"type":"output","why":""}}],
"indicators":[{{"indicator":"","shows":"","source":"","frequency":""}}],"gap":""}}"""


def analyse(outcome: dict, llm: LLM) -> dict:
    actions = "\n".join(f"{i}. {a}" for i, a in enumerate(outcome["actions"], 1))
    raw = parse_json(llm.complete(ANALYSE_PROMPT.format(name=outcome["name"], actions=actions), max_tokens=3000))
    return verify_analysis(raw, outcome)


def verify_analysis(result: dict, outcome: dict) -> dict:
    n, seen, rows, warnings = len(outcome["actions"]), set(), [], []
    for a in result.get("actions", []):
        num = a.get("number")
        if not isinstance(num, int) or not 1 <= num <= n or num in seen or a.get("type") not in ("output", "outcome"):
            warnings.append(f"Ignored an invalid or duplicate classification: {a}")
            continue
        seen.add(num)
        rows.append({"number": num, "action": outcome["actions"][num - 1], "type": a["type"], "why": a.get("why", "")})
    missing = [i for i in range(1, n + 1) if i not in seen]
    if missing:
        warnings.append("Not classified, check by hand: actions " + ", ".join(map(str, missing)))
    indicators = result.get("indicators", [])
    for ind in indicators:
        if not ind.get("source") or not ind.get("frequency"):
            warnings.append(f"Indicator without a data source or frequency: {ind.get('indicator', '?')}")
    return {"outcome": outcome["name"], "actions": sorted(rows, key=lambda r: r["number"]), "missing": missing,
            "indicators": indicators, "gap": result.get("gap", ""), "warnings": warnings}


def draft_update(outcome: dict, statuses: dict[str, str], audience: str, llm: LLM, note: str = "") -> dict:
    if audience not in AUDIENCES:
        raise ValueError(f"Audience must be one of: {', '.join(AUDIENCES)}")
    bad = [s for s in statuses.values() if s not in STATUSES]
    if bad:
        raise ValueError(f"Unknown status: {bad[0]}. Use one of: {', '.join(STATUSES)}")
    lines = "\n".join(f"- {a}: {s}" for a, s in statuses.items())
    prompt = (f'Draft a quarterly progress update on this outcome: "{outcome["name"]}"\n\nAction statuses:\n{lines}\n'
              + (f"Note from the consultant: {note}\n" if note else "")
              + f"\n{AUDIENCES[audience]}\nReport only what the statuses show. Never invent figures, dates or results. "
              "Say plainly where actions are at risk or behind. Separate work done from evidence of change for people. Plain text.")
    text = llm.complete(prompt, max_tokens=1200).strip()
    allowed = set(re.findall(r"\d+(?:\.\d+)?", outcome["name"] + lines + note))
    unsupported = sorted({x for x in re.findall(r"\d+(?:\.\d+)?", text) if x not in allowed})
    return {"text": text, "unsupported_numbers": unsupported}


def to_markdown(result: dict) -> str:
    out = [f"# Outcome analysis: {result['outcome']}", ""]
    for w in result["warnings"]:
        out.append(f"> WARNING: {w}")
    for label, kind in (("Outputs: work done", "output"), ("Outcomes: change for people", "outcome")):
        out += ["", f"## {label}", ""]
        out += [f"- {r['action']}. _{r['why']}_" for r in result["actions"] if r["type"] == kind] or ["- None"]
    out += ["", "## Proposed indicators", "", "| Indicator | What it shows | Data source | How often |", "| --- | --- | --- | --- |"]
    out += [f"| {i.get('indicator', '')} | {i.get('shows', '')} | {i.get('source', '')} | {i.get('frequency', '')} |"
            for i in result["indicators"]]
    if result["gap"]:
        out += ["", f"**Biggest measurement gap:** {result['gap']}"]
    out += ["", "_AI first draft. A consultant checks each classification and indicator with the client._"]
    return "\n".join(out)

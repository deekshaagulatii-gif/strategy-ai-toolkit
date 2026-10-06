"""Consultation Analyser: groups free-text responses into themes and checks every quote against its source.

AI does the first sort. The code then verifies, so a consultant can see at a glance:
  - which quotes appear word for word in the response they are attributed to
  - which responses were not placed in any theme
  - which less common points need reading by hand
"""
from __future__ import annotations

import csv
from pathlib import Path

from .llm import LLM, parse_json
from .text import normalise

PROMPT = """You are helping a strategy consultant analyse free-text consultation responses.
Question asked: "{question}"

Responses (ID then text):
{responses}

Tasks:
1. Identify 4 to 7 themes. A response can belong to more than one theme. Name each theme in plain English (under 8 words) and describe it in one sentence.
2. For each theme, list the numeric IDs of every response that expresses it.
3. For each theme, give one supporting quote copied EXACTLY, word for word, from one response, under 20 words, with its response ID. Do not paraphrase the quote.
4. List points raised by only one or two responses that a consultant should not miss, especially from minority or seldom-heard groups.

Return ONLY JSON:
{{"themes":[{{"name":"","description":"","response_ids":[1,2],"quote":{{"response_id":1,"text":""}}}}],
 "less_common":[{{"response_id":8,"point":"one sentence"}}]}}"""


def load_responses(path: str | Path) -> list[str]:
    """Read a CSV with a 'response' column (one row per response)."""
    with open(path, newline="", encoding="utf-8") as f:
        return [row["response"].strip() for row in csv.DictReader(f) if row.get("response", "").strip()]


def verify(result: dict, responses: list[str]) -> dict:
    """Add checks to the model's result. Never trusts the model's IDs or quotes without testing them."""
    n = len(responses)
    covered: set[int] = set()
    for theme in result.get("themes", []):
        ids = sorted({int(i) for i in theme.get("response_ids", []) if str(i).isdigit() and 1 <= int(i) <= n})
        theme["response_ids"] = ids
        theme["count"] = len(ids)
        covered.update(ids)
        quote = theme.get("quote") or {}
        qid = int(quote.get("response_id", 0) or 0)
        source = responses[qid - 1] if 1 <= qid <= n else ""
        quote["verified"] = bool(quote.get("text")) and normalise(quote["text"]) in normalise(source)
        theme["quote"] = quote
    result["themes"] = sorted(result.get("themes", []), key=lambda t: -t["count"])
    result["unassigned"] = [i for i in range(1, n + 1) if i not in covered]
    result["total_responses"] = n
    return result


def analyse(responses: list[str], llm: LLM, question: str) -> dict:
    if len(responses) < 3:
        raise ValueError("Provide at least three responses.")
    listing = "\n".join(f"R{i}: {r}" for i, r in enumerate(responses, start=1))
    raw = llm.complete(PROMPT.format(question=question, responses=listing), max_tokens=3000)
    return verify(parse_json(raw), responses)


def to_markdown(result: dict, question: str) -> str:
    n = result["total_responses"]
    lines = [f"# Consultation analysis (first draft)", "", f"Question: {question}", f"Responses analysed: {n}", ""]
    for t in result["themes"]:
        q = t["quote"]
        mark = "verified" if q.get("verified") else "NOT FOUND IN SOURCE: check by hand"
        lines += [
            f"## {t.get('name', 'Theme')} ({t['count']} of {n})",
            t.get("description", ""),
            "",
            f"> \"{q.get('text', '')}\" (R{q.get('response_id', '?')}, quote {mark})",
            "",
            "Responses: " + ", ".join(f"R{i}" for i in t["response_ids"]),
            "",
        ]
    if result.get("less_common"):
        lines += ["## Less common points to read by hand", ""]
        lines += [f"- {p.get('point', '')} (R{p.get('response_id', '?')})" for p in result["less_common"]]
        lines.append("")
    if result["unassigned"]:
        lines.append("Not placed in any theme: " + ", ".join(f"R{i}" for i in result["unassigned"]))
    lines += ["", "_AI first draft. A consultant must review every theme before use._"]
    return "\n".join(lines)

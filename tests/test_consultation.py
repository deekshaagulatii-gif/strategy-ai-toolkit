import json

import pytest

from toolkit import consultation

RESPONSES = [
    "Inspection reports take too long to be published.",
    "Please publish inspection findings faster and in plain language.",
    "Home support needs regulating urgently.",
    "I am Deaf and use Irish Sign Language. Reports are never available in ISL.",
]


def model_reply(quote_text, quote_id=1, ids=(1, 2, 99)):
    return "```json\n" + json.dumps({
        "themes": [
            {"name": "Faster reports", "description": "d", "response_ids": list(ids), "quote": {"response_id": quote_id, "text": quote_text}},
            {"name": "Home support", "description": "d", "response_ids": [3], "quote": {"response_id": 3, "text": "Home support needs regulating"}},
        ],
        "less_common": [{"response_id": 4, "point": "ISL access"}],
    }) + "\n```"


def test_exact_quote_is_verified(fake_llm):
    result = consultation.analyse(RESPONSES, fake_llm(model_reply("take too long to be published")), "Q")
    assert result["themes"][0]["quote"]["verified"] is True


def test_quote_ignores_case_and_curly_punctuation(fake_llm):
    result = consultation.analyse(RESPONSES, fake_llm(model_reply("“Inspection REPORTS take too long”")), "Q")
    assert result["themes"][0]["quote"]["verified"] is True


def test_invented_quote_is_flagged(fake_llm):
    result = consultation.analyse(RESPONSES, fake_llm(model_reply("reports are a disgrace")), "Q")
    assert result["themes"][0]["quote"]["verified"] is False


def test_quote_attributed_to_wrong_response_is_flagged(fake_llm):
    result = consultation.analyse(RESPONSES, fake_llm(model_reply("take too long to be published", quote_id=3)), "Q")
    assert result["themes"][0]["quote"]["verified"] is False


def test_out_of_range_ids_are_dropped_and_gaps_reported(fake_llm):
    result = consultation.analyse(RESPONSES, fake_llm(model_reply("take too long")), "Q")
    assert result["themes"][0]["response_ids"] == [1, 2]
    assert result["unassigned"] == [4]


def test_themes_sorted_by_size(fake_llm):
    result = consultation.analyse(RESPONSES, fake_llm(model_reply("take too long")), "Q")
    assert [t["count"] for t in result["themes"]] == [2, 1]


def test_needs_at_least_three_responses(fake_llm):
    with pytest.raises(ValueError):
        consultation.analyse(RESPONSES[:2], fake_llm("{}"), "Q")


def test_markdown_marks_unverified_quotes(fake_llm):
    result = consultation.analyse(RESPONSES, fake_llm(model_reply("made up words")), "Q")
    assert "NOT FOUND IN SOURCE" in consultation.to_markdown(result, "Q")


def test_sample_csv_loads():
    assert len(consultation.load_responses("data/sample_responses.csv")) == 22

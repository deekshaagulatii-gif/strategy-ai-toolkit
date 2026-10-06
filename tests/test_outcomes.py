import json

import pytest

from toolkit import outcomes

OUTCOME = {"name": "People get safer services", "actions": ["Publish inspection reports", "Reduce repeat incidents", "Train inspectors"]}


def analysis(actions, indicators=None):
    return json.dumps({"actions": actions, "gap": "No baseline.",
                       "indicators": indicators or [{"indicator": "Repeat incidents", "shows": "", "source": "Inspection data", "frequency": "Quarterly"}]})


def test_every_action_classified_once(fake_llm):
    reply = analysis([{"number": 1, "type": "output", "why": ""}, {"number": 1, "type": "outcome", "why": ""},
                      {"number": 9, "type": "output", "why": ""}, {"number": 2, "type": "outcome", "why": ""}])
    r = outcomes.analyse(OUTCOME, fake_llm(reply))
    assert [a["number"] for a in r["actions"]] == [1, 2]
    assert r["missing"] == [3]
    assert any("actions 3" in w for w in r["warnings"])


def test_indicator_without_source_is_flagged(fake_llm):
    reply = analysis([{"number": i, "type": "output", "why": ""} for i in (1, 2, 3)],
                     [{"indicator": "Satisfaction", "shows": "", "source": "", "frequency": "Yearly"}])
    assert any("Satisfaction" in w for w in outcomes.analyse(OUTCOME, fake_llm(reply))["warnings"])


def test_invented_figure_is_flagged(fake_llm):
    statuses = {a: "On track" for a in OUTCOME["actions"]}
    r = outcomes.draft_update(OUTCOME, statuses, "board", fake_llm("All 3 actions on track; incidents fell 40%."))
    assert r["unsupported_numbers"] == ["3", "40"]


def test_bad_inputs_rejected(fake_llm):
    with pytest.raises(ValueError):
        outcomes.draft_update(OUTCOME, {"Train inspectors": "Done-ish"}, "board", fake_llm(""))
    with pytest.raises(ValueError):
        outcomes.draft_update(OUTCOME, {}, "minister", fake_llm(""))


def test_sample_data_loads():
    data = outcomes.load_outcomes()
    assert len(data) == 6 and all(o["actions"] for o in data)

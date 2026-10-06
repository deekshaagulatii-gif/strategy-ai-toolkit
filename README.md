# Strategy AI Toolkit

Three working models of how AI can support a strategy consultancy, in the order they are used on a project:
**win the work, research it, and track whether the strategy delivers.**

**Try it:** [live demo](https://claude.ai/artifact/4qnuaZiebVm4hx2ZM33Gkh) · Built by [Deeksha Gulati](https://deekshagulati.netlify.app) using public documents and fictional sample data only.

![tests](https://github.com/deekshaagulatii-gif/strategy-ai-toolkit/actions/workflows/tests.yml/badge.svg)

---

## The three tools

| Tool | Stage | What AI does | What the code checks |
| --- | --- | --- | --- |
| **1. Tender Fit Checker** | Win the work | Lists a tender's mandatory requirements and weighted award criteria, then rates how well a draft response addresses each one: *addressed well*, *mentioned briefly* or *missing* | Every evidence quote must appear word for word in the draft, or the rating is not trusted. Every weight must appear in the tender, and weights must total 100%. Gaps are ranked by marks at risk, mandatory gaps first |
| **2. Consultation Analyser** | Research | Groups free-text stakeholder responses into themes, counts them and picks an example quote for each | Every quote is matched word for word against the response it is attributed to. Responses left out of every theme are listed. Less common points are flagged for a person to read |
| **3. Outcome Tracker** | Track results | Separates a plan's actions into outputs (work done) and outcomes (change for people), proposes indicators, and drafts the progress update for the board, staff or public | Every action must be classified exactly once. Every indicator needs a data source and frequency. Any number in the draft update that is not in the inputs is flagged |

**The principle throughout:** AI does the first draft, the consultant checks it, and every result can be traced back to its source.

## Why it is built this way

- **No free public chatbots.** The Irish Government's *Guidelines for the Responsible Use of AI in the Public Service* (May 2025) advise against free generative AI tools because information entered could be used to train the model. This toolkit calls a model through a business API and can be pointed at a private **Azure OpenAI deployment in an EU region** instead (`toolkit/llm.py`).
- **Checks in code, not just in the prompt.** Asking a model "don't make things up" is not enough. The code tests each quote, weight and figure, and shows the result on screen.

## Data

- `data/sample_tender.txt`, `data/sample_draft.txt`: a **fictional** request for tender and a deliberately incomplete draft response.
- `data/sample_responses.csv`: 22 **illustrative** consultation responses, written for this demo.
- `data/hiqa_outcomes.json`: outcomes and actions from HIQA's public [Corporate Plan 2025–2027](https://www.hiqa.ie/sites/default/files/2025-05/HIQA-Corporate-Plan-25-27.pdf), lightly abridged. Statuses used in the demo are illustrative, not HIQA's real progress.

## Run it

```bash
git clone https://github.com/deekshaagulatii-gif/strategy-ai-toolkit.git
cd strategy-ai-toolkit
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key        # or put it in a .env file

python cli.py tender  data/sample_tender.txt data/sample_draft.txt
python cli.py consult data/sample_responses.csv
python cli.py outcome 1
streamlit run app.py                      # the web version
```

To use a private Azure deployment instead, set `LLM_PROVIDER=azure_openai` with `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_DEPLOYMENT`.

**Hosting:** the web app runs on Streamlit Community Cloud. Add `ANTHROPIC_API_KEY` and an optional `APP_PASSWORD` under the app's **Secrets**, never in the code.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

18 tests run automatically on every change (GitHub Actions). They use a fake model, so no API key is needed, and they check the safeguards above: invented or misattributed quotes, ratings without evidence, invented weights, unclassified actions and invented figures are all caught.

## Project structure

```
app.py                  Streamlit web app (three tabs)
cli.py                  Command-line version
toolkit/tender.py       Tender Fit Checker
toolkit/consultation.py Consultation Analyser
toolkit/outcomes.py     Outcome Tracker
toolkit/llm.py          Choice of AI provider (Anthropic or private Azure OpenAI)
toolkit/text.py         Text normalisation used by the quote checks
data/                   Sample data
tests/                  Automated tests
web/index.html          The polished browser demo
```

## Licence

MIT

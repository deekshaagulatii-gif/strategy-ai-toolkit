"""Command-line entry point.

  python cli.py tender   data/sample_tender.txt data/sample_draft.txt
  python cli.py consult  data/sample_responses.csv
  python cli.py outcome  1

Results are printed and saved to the output/ folder as Markdown.
"""
import argparse
from pathlib import Path

from dotenv import load_dotenv

from toolkit import consultation, outcomes, tender
from toolkit.llm import get_llm

DEFAULT_QUESTION = "What should a national health and social care regulator prioritise over the next three years?"
OUT = Path("output")


def save(name: str, text: str) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(text, encoding="utf-8")
    print(f"\nSaved to {OUT / name}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Strategy AI Toolkit")
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("tender", help="Check a draft tender response against the tender's criteria")
    t.add_argument("tender_file")
    t.add_argument("draft_file")
    c = sub.add_parser("consult", help="Find themes in consultation responses (CSV with a 'response' column)")
    c.add_argument("csv")
    c.add_argument("--question", default=DEFAULT_QUESTION)
    o = sub.add_parser("outcome", help="Separate outputs from outcomes for one outcome of the sample plan (1-6)")
    o.add_argument("number", type=int)
    args = parser.parse_args()

    llm = get_llm()
    if args.command == "tender":
        md = tender.to_markdown(tender.check(Path(args.tender_file).read_text(), Path(args.draft_file).read_text(), llm))
        name = "tender_fit_check.md"
    elif args.command == "consult":
        md = consultation.to_markdown(consultation.analyse(consultation.load_responses(args.csv), llm, args.question), args.question)
        name = "consultation_analysis.md"
    else:
        md = outcomes.to_markdown(outcomes.analyse(outcomes.load_outcomes()[args.number - 1], llm))
        name = f"outcome_{args.number}.md"
    print(md)
    save(name, md)


if __name__ == "__main__":
    main()

"""Ask a question from the command line.

    python -m rag.ask "Where is the emergency stop on the BellaBot Pro?"
    python -m rag.ask "Welcher Roboter passt durch einen 60 cm breiten Gang?" --debug
"""

from __future__ import annotations

import argparse
import sys

from .pipeline import answer


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question")
    ap.add_argument("--product", nargs="+", metavar="PRODUCT_ID")
    ap.add_argument("--lang")
    ap.add_argument("--debug", action="store_true", help="show tool calls and checks")
    args = ap.parse_args()

    result = answer(args.question, lang=args.lang, product_ids=args.product)
    print(f"\n{result['answer']}\n")
    print(f"status: {result['status']} · language: {result['language']} · {result['debug']['seconds']} s")
    for n, s in enumerate(result["sources"], start=1):
        print(f"  [{n}] {s['product_name']} · {s['section_id']} {s['section_title']} · p.{s['page']} ({s['lang']})")
        for f in s["figures"]:
            print(f"        figure: {f['path']}  ({len(f['labels'])} labels)")
    if args.debug:
        d = result["debug"]
        print("\ntool calls:")
        for c in d["tool_calls"]:
            print(f"  {c['tool']} {c['args']}")
        audit = result.get("number_audit") or {}
        verified = [f"{v['value']}->{v['sources']}" for v in audit.get("verified", [])]
        print(f"evidence sources: {d['evidence_sources']} · hit max rounds: {d['hit_max_rounds']} "
              f"· verified numbers: {verified} · unverified numbers: {audit.get('unverified', [])} "
              f"· dropped figures: {d['dropped_figure_ids']}")


if __name__ == "__main__":
    main()

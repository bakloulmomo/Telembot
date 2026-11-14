"""Run the test questions through the RAG engine and check the answers.

    python eval/run_eval.py                 # all questions
    python eval/run_eval.py fig-1 de-2      # only these ids
    python eval/run_eval.py --show          # also print every answer

Checks per question (only those the question defines):
  status      the answer status is one of the expected ones (default: answered)
  products    each expected product is among the cited sources
  contains    the answer contains one text of every group (case-insensitive)
  figure      a returned figure id starts with the expected text
  no_figures  no figure is returned
  language    the reported answer language
  source_lang at least one cited source is in this language
Results are saved to eval/last_run.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR))

from rag.pipeline import answer  # noqa: E402


def evaluate(q: dict) -> dict:
    try:
        r = answer(q["q"], history=q.get("history"))
    except Exception as exc:  # noqa: BLE001
        return {"id": q["id"], "passed": False, "failed": [f"error: {exc}"], "result": None}
    text = r["answer"].lower().replace(" ", " ")
    cited = {s["product_id"] for s in r["sources"]}
    figures = [f["id"] for s in r["sources"] for f in s["figures"]]
    failed = []
    if r["status"] not in q.get("status", ["answered"]):
        failed.append(f"status {r['status']}")
    for pid in q.get("products", []):
        if pid not in cited:
            failed.append(f"product {pid} not cited")
    for group in q.get("contains", []):
        if not any(g.lower() in text for g in group):
            failed.append(f"answer lacks {' / '.join(group)}")
    if "figure" in q and not any(f.startswith(q["figure"]) for f in figures):
        failed.append(f"figure {q['figure']} not returned (got {figures})")
    if q.get("no_figures") and figures:
        failed.append(f"unexpected figures {figures}")
    if "language" in q and r["language"][:2].lower() != q["language"]:
        failed.append(f"language {r['language']}")
    if "source_lang" in q and not any(s["lang"] == q["source_lang"] for s in r["sources"]):
        failed.append(f"no source in {q['source_lang']}")
    if r["debug"]["unsupported_numbers"]:
        failed.append(f"numbers not in evidence: {r['debug']['unsupported_numbers']}")
    return {"id": q["id"], "passed": not failed, "failed": failed, "result": r}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    questions = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))
    if args.ids:
        questions = [q for q in questions if q["id"] in args.ids]
    with ThreadPoolExecutor(args.workers) as pool:
        outcomes = list(pool.map(evaluate, questions))

    seconds = []
    for q, o in zip(questions, outcomes):
        r = o["result"]
        secs = r["debug"]["seconds"] if r else 0
        seconds.append(secs)
        print(f"{'PASS' if o['passed'] else 'FAIL'}  {q['id']:<7} {q['type']:<40} {secs:>5.1f}s  {'; '.join(o['failed'])}")
        if r and (args.show or not o["passed"]):
            print(f"        Q: {q['q']}")
            print("        A: " + r["answer"].replace("\n", "\n           "))
            for n, s in enumerate(r["sources"], start=1):
                figs = ", ".join(f["id"] for f in s["figures"])
                print(f"           [{n}] {s['product_id']} {s['section_id']} p.{s['page']} ({s['lang']})"
                      + (f"  figures: {figs}" if figs else ""))
            print("           tools: " + " | ".join(f"{c['tool']} {c['args']}" for c in r["debug"]["tool_calls"]))
    passed = sum(o["passed"] for o in outcomes)
    print(f"\n{passed}/{len(outcomes)} passed · average {sum(seconds) / max(len(seconds), 1):.1f} s · slowest {max(seconds):.1f} s")
    (Path(__file__).parent / "last_run.json").write_text(
        json.dumps([{"id": o["id"], "passed": o["passed"], "failed": o["failed"], "question": q["q"],
                     "answer": o["result"]["answer"] if o["result"] else None,
                     "status": o["result"]["status"] if o["result"] else None,
                     "sources": [{k: s[k] for k in ("product_id", "lang", "section_id", "page")} | {"figures": [f["id"] for f in s["figures"]]}
                                 for s in o["result"]["sources"]] if o["result"] else [],
                     "tool_calls": o["result"]["debug"]["tool_calls"] if o["result"] else []}
                    for q, o in zip(questions, outcomes)], ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(0 if passed == len(outcomes) else 1)


if __name__ == "__main__":
    main()

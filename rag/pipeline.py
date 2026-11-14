"""Question in, grounded answer out.

    from rag.pipeline import answer
    result = answer("Where is the emergency stop on the BellaBot Pro?")

The return value follows the contract in docs/6_project_plan.md (section 5.2):
answer, status, language, sources (with figures). Source numbers in the answer
text are the positions in `sources`, starting at 1.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Callable

from . import checks, store
from .tools import TOOLS, Evidence, tool_schemas

log = logging.getLogger("rag")

MAX_TOOL_ROUNDS = 3
MAX_FIGURES = 3

ANSWER_SCHEMA = {
    "name": "answer",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["answer", "status", "language", "figure_ids", "gaps", "options", "notes"],
        "properties": {
            "answer": {"type": "string",
                       "description": "The answer in the user's language, with [n] source markers. Markdown allowed."},
            "status": {"type": "string", "enum": ["answered", "not_in_docs", "needs_clarification"]},
            "language": {"type": "string", "description": "ISO 639-1 code of the answer's language, e.g. en, de, it."},
            "figure_ids": {"type": "array", "items": {"type": "string"},
                           "description": "Ids of figures to show with the answer, most useful first. Usually empty."},
            "gaps": {"type": "array", "items": {"type": "string"},
                     "description": "Parts of the question the manuals do not answer, one short sentence each."},
            "options": {"type": "array", "items": {"type": "string"},
                        "description": "Only with status needs_clarification: the choices offered to the user."},
            "notes": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["source", "note"],
                "properties": {"source": {"type": "integer"}, "note": {"type": "string"}}},
                "description": "One entry per cited source: how the answer uses it."},
        },
    },
}


def system_prompt() -> str:
    catalog = "\n".join(
        f"- {p.id}: {p.name} ({p.kind}, {p.family})" + (f" — {p.overview['en'][:160]}" if p.overview.get("en") else "")
        for p in store.products().values())
    return f"""You answer questions about PUDU service robots and their accessories, using only the product manuals.

Users are technicians (exact values, procedures, troubleshooting) and non-technical people such as sales staff
(which product fits a need, differences between products).

# Products
{catalog}

# How to work
1. Call tools to get evidence before answering. You may call several tools at once. At most {MAX_TOOL_ROUNDS} rounds.
   - search_manuals: procedures, troubleshooting, indicators, parts, safety, accessories and compatibility, details.
   - get_specs: exact specification values and side-by-side comparison.
   - find_products: "which robot…" questions on one specification parameter.
   A general need ("narrow aisles", "heavy loads", "long shifts") maps to a parameter (min_passage_width, max_load, battery_runtime).
2. Answer only from the tool results. Do not use anything you know about PUDU or robots from elsewhere.

# Rules for the answer
- Write in the language of the user's question, whatever the language of the sources.
- Put a source marker like [3] right after each statement, using the numbers shown in the tool results.
- Copy numbers and units exactly as printed. Never convert, round or calculate a value.
- If a value depends on a model, mode or condition, say which one it applies to.
- Safety warnings and procedure steps: keep the manual's meaning and order; do not leave steps out.
- If the question does not name a model and the answer differs between similar models (for example CC1 and CC1 Pro,
  BellaBot and BellaBot Pro), give the answer for each model separately, or ask which one is meant.
- If the manuals do not contain the answer, say so plainly and set status to "not_in_docs". Do not guess.
- If they answer only part of the question, answer that part (status "answered") and put each part they do not
  answer in gaps, one short sentence each, without numbers, for example "The manuals do not list prices.".
  Do not repeat the gaps in the answer text.
  The manuals contain no prices, availability or delivery times. A product missing from a compatibility list
  is "not listed in the documentation", not "incompatible".
- A recommendation must name the specification it is based on.
- Be brief: answer first, then only the details that matter. No introduction, no closing remarks.
- Do not add advice that is not in the tool results (for example "contact support" or "consult the manual"),
  unless the manual itself says it.
- Source markers contain only numbers, like [1] or [2][3]. Never put other text in square brackets.

# Figures
Tool results show figures as [FIGURE id] where they appear in the manual. Put an id in figure_ids only when the
picture helps: the question is about where a part is or what something looks like, or the answer is a procedure
step that the figure shows. At most {MAX_FIGURES}. For a numbered part, mention its number in the answer.
Text marked "Figure description (AI)" was written by an AI, not printed in the manual: do not quote it as a fact.
When asked where a part is, give its number in the figure (and the view, if the manual names one). Do not describe
its position in your own words ("at the front", "below the screen"): you cannot see the figure, the user can.

# Notes on sources
For every source number you cite, add one entry to notes: in one or two sentences, what the manual says there and
how the answer uses it. Say so if the answer's wording is stronger, weaker or more general than the manual's.
Write the notes in the language of the answer. Never invent manual text.

# Status
- "answered": the manuals answer the question.
- "not_in_docs": they do not.
- "needs_clarification": you need to know which product or model is meant; ask one short question, and put
  2 to 5 short choices in options (product names, plus a choice like "Compare both" when that makes sense).
  Otherwise options is empty."""


def _chat(messages: list[dict], tools: list[dict] | None, must_use_tool: bool = False):
    kwargs: dict = {"model": store.CHAT_MODEL, "messages": messages,
                    "response_format": {"type": "json_schema", "json_schema": ANSWER_SCHEMA}}
    if tools:
        kwargs["tools"] = tools
        if must_use_tool:
            kwargs["tool_choice"] = "required"
    if store.CHAT_MODEL.startswith("gpt-4"):
        kwargs["temperature"] = 0
    return store.client().chat.completions.create(**kwargs).choices[0].message


def _run_tool(evidence: Evidence, conn, name: str, raw_args: str) -> str:
    try:
        args = json.loads(raw_args or "{}")
        return TOOLS[name](evidence, conn, **args)
    except KeyError:
        return f"Error: unknown tool '{name}'."
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return f"Error: {exc}"


def answer(question: str, history: list[dict] | None = None, lang: str | None = None,
           product_ids: list[str] | None = None, progress: Callable[[dict], None] | None = None) -> dict:
    """Answer one question.

    history: earlier turns as [{"role": "user" | "assistant", "content": "..."}].
    lang: force the answer language (en, de, it, ...); None = language of the question.
    product_ids: products chosen in the interface; None = found from the question.
    progress: called with {"step": "search" | "read" | "check", "detail": "..."} as the work advances.
    """
    started = time.perf_counter()

    def emit(step: str, detail: str) -> None:
        if progress:
            try:
                progress({"step": step, "detail": detail})
            except Exception:  # noqa: BLE001  a broken listener must not break the answer
                log.exception("progress callback failed")

    evidence = Evidence()
    catalog = store.products()

    hints = []
    selected = [p for p in product_ids or [] if p in catalog]
    if selected:
        hints.append("The user selected these products in the interface: " + ", ".join(selected)
                     + ". Answer about them unless the question clearly names another product.")
    else:
        named = store.find_products_in_text(question)
        if named:
            hints.append("Product names found in the question: "
                         + ", ".join(f"{catalog[p].name} = {p}" for p in named) + ".")
    if lang:
        hints.append(f"Answer in this language: {lang}.")

    messages: list[dict] = [{"role": "system", "content": system_prompt()}]
    for turn in (history or [])[-8:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question + ("\n\n(" + " ".join(hints) + ")" if hints else "")})

    tool_calls_log: list[dict] = []
    tools = tool_schemas()
    with store.connect() as conn:
        message = None
        for round_no in range(MAX_TOOL_ROUNDS + 1):
            last_round = round_no == MAX_TOOL_ROUNDS
            # First round: always look in the manuals, never answer from memory or from the chat history.
            message = _chat(messages, None if last_round else tools, must_use_tool=round_no == 0)
            if not message.tool_calls:
                break
            messages.append({"role": "assistant", "content": message.content,
                             "tool_calls": [c.model_dump() for c in message.tool_calls]})
            for call in message.tool_calls:
                emit("search", _describe_call(call.function.name, call.function.arguments))
                result = _run_tool(evidence, conn, call.function.name, call.function.arguments)
                tool_calls_log.append({"tool": call.function.name, "args": call.function.arguments})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
            emit("read", _describe_evidence(evidence))

        result = _parse(message.content)
        n_values = checks.count_numbers(result["answer"])
        emit("check", f"Checking {n_values} value{'s' if n_values != 1 else ''} against the manual pages"
             if n_values else "Checking the answer against the manual pages")

        # Check: numbers in the answer must come from the evidence. One retry.
        missing = checks.unsupported_numbers(result["answer"], evidence.text(), question)
        if missing and result["status"] == "answered":
            messages.append({"role": "assistant", "content": message.content})
            messages.append({"role": "user", "content":
                             "These numbers in your answer are not in the tool results: " + ", ".join(missing)
                             + ". Rewrite the answer using only values printed in the tool results, copied exactly. "
                               "If the value is not there, say the manuals do not state it."})
            retry = _parse(_chat(messages, None).content)
            still = checks.unsupported_numbers(retry["answer"], evidence.text(), question)
            if len(still) < len(missing):
                result, missing = retry, still
        if n_values and not missing:
            emit("check", f"All {n_values} value{'s' if n_values != 1 else ''} found in the manuals")
        elif missing:
            emit("check", f"{len(missing)} value{'s' if len(missing) != 1 else ''} not found in the manuals")

    return _finish(result, evidence, missing, tool_calls_log, started)


def _manual_names(product_ids) -> str:
    catalog = store.products()
    names = [catalog[p].name for p in product_ids or [] if p in catalog]
    if not names:
        return ""
    if len(names) == 1:
        return f"{names[0]} User Manual"
    return ", ".join(names[:-1]) + f" and {names[-1]} manuals"


def _describe_call(name: str, raw_args: str) -> str:
    """One line for the interface about what a tool call is doing."""
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        args = {}
    catalog = store.products()
    if name == "search_manuals":
        names = _manual_names(args.get("product_ids"))
        return f"Now reading: {names}" if names else f"Searching all {len(catalog)} manuals"
    if name == "get_specs":
        names = [catalog[p].name for p in args.get("product_ids") or [] if p in catalog]
        return "Now reading: the specifications of " + (", ".join(names) or "the products")
    if name == "find_products":
        param = store.PARAM_BY_KEY.get(args.get("parameter"), {}).get("labels", {}).get("en", "a specification")
        scope = args.get("family") or args.get("kind") or "robot"
        return f"Comparing {param.lower()} across every {scope} manual"
    return "Searching the manuals"


def _describe_evidence(evidence: Evidence) -> str:
    products = list(dict.fromkeys(s.product_id for s in evidence.sources))
    sections = len(evidence.sources)
    if not sections:
        return "No matching pages"
    manuals = _manual_names(products) if len(products) <= 2 else f"{len(products)} manuals"
    return f"{sections} section{'s' if sections != 1 else ''} from the {manuals}"


def _parse(content: str | None) -> dict:
    try:
        data = json.loads(content or "")
        return {"answer": str(data["answer"]), "status": data["status"], "language": data.get("language", "en"),
                "figure_ids": list(data.get("figure_ids") or []),
                "gaps": [str(g) for g in data.get("gaps") or [] if str(g).strip()],
                "options": [str(o) for o in data.get("options") or [] if str(o).strip()],
                "notes": {int(n["source"]): str(n["note"]) for n in data.get("notes") or []
                          if isinstance(n, dict) and str(n.get("source", "")).isdigit()}}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return {"answer": content or "", "status": "answered", "language": "en", "figure_ids": [],
                "gaps": [], "options": [], "notes": {}}


def _finish(result: dict, evidence: Evidence, unsupported: list[str], tool_calls: list[dict], started: float) -> dict:
    by_n = {s.n: s for s in evidence.sources}
    cited = [n for n in checks.cited_numbers(result["answer"]) if n in by_n]
    if result["status"] == "not_in_docs":
        # Nothing in the manuals supports the answer, so there is nothing to cite:
        # the sections the model looked at are not sources of "it is not there".
        cited, result["figure_ids"] = [], []

    # Figures: only ids that are in the evidence. A figure's section becomes a source even if not cited in the text.
    figure_ids = [f for f in dict.fromkeys(result["figure_ids"]) if f in evidence.figure_ids][:MAX_FIGURES]
    for fid in figure_ids:
        owner = next(s.n for s in evidence.sources if any(f["id"] == fid for f in s.figures))
        if owner not in cited:
            cited.append(owner)

    mapping = {old: new for new, old in enumerate(cited, start=1)}
    sources = []
    for old in cited:
        s = by_n[old]
        sources.append({
            "text": s.text[:1500],
            "product_id": s.product_id,
            "product_name": store.products()[s.product_id].name,
            "lang": s.lang,
            "section_id": s.section_id,
            "section_title": s.title,
            "page": s.page,
            "pdf_page": s.pdf_page,
            "score": s.score,
            "figures": [{"id": f["id"], "path": f["path"], "caption": f["caption"], "labels": f["labels"]}
                        for f in s.figures if f["id"] in figure_ids],
            "note": checks.strip_tags(checks.renumber(result["notes"][old], mapping)) if old in result["notes"] else None,
        })

    status = result["status"]
    if status == "answered" and not sources:
        status = "not_in_docs"          # an answer with no source behind it is not grounded
    out = {
        "answer": checks.strip_tags(checks.renumber(result["answer"], mapping)),
        "status": status,
        "language": result["language"],
        "gaps": [checks.strip_tags(g) for g in result["gaps"]],
        "options": result["options"][:5] if status == "needs_clarification" else [],
        "sources": sources,
        "debug": {
            "model": store.CHAT_MODEL,
            "tool_calls": tool_calls,
            "evidence_sources": len(evidence.sources),
            "unsupported_numbers": unsupported,
            "dropped_figure_ids": [f for f in result["figure_ids"] if f not in evidence.figure_ids],
            "seconds": round(time.perf_counter() - started, 1),
        },
    }
    log.info("status=%s sources=%d figures=%d tools=%d seconds=%.1f", status, len(sources),
             sum(len(s["figures"]) for s in sources), len(tool_calls), out["debug"]["seconds"])
    return out


def search(query: str, product_ids: list[str] | None = None, lang: str | None = None, k: int = 8) -> list[dict]:
    """Retrieval only, for the /api/search endpoint."""
    with store.connect() as conn:
        rows = store.vector_search(conn, query, [p for p in product_ids or [] if p in store.products()] or None, lang, k)
    return [{"text": r[8][:1500], "product_id": r[1], "lang": r[2], "section_id": r[3], "section_title": r[4],
             "page": r[6], "pdf_page": r[7], "score": round(r[11], 4)} for r in rows]

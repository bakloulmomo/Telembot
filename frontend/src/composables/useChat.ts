// La conversazione: un turno per domanda, con passi di avanzamento, chiarimento, risposta e fonti.

import { computed, reactive, ref } from "vue";
import { plainAnswer } from "@/lib/answer";
import { streamChat, type Citation, type Done, type HistoryMessage } from "@/lib/api";

export type StepKey = "search" | "read" | "check";
export type StepState = "pending" | "active" | "done" | "paused";
export interface Step { key: StepKey; state: StepState; detail: string }

export type Phase = "working" | "answering" | "clarify" | "done" | "error" | "stopped";

export interface Clarify { question: string; detail: string; options: string[]; text: string }

export interface Turn {
  id: number;
  question: string;
  clarifiedWith: string | null;   // la scelta data al chiarimento, es. "BellaBot Pro"
  clarifyText: string | null;     // la domanda di chiarimento, per la cronologia
  phase: Phase;
  steps: Step[];
  answer: string;
  citations: Citation[];
  done: Done | null;
  clarify: Clarify | null;
  error: string | null;
}

const STEP_KEYS: StepKey[] = ["search", "read", "check"];
const HISTORY_MAX = 10;

function freshSteps(): Step[] {
  return STEP_KEYS.map((key, i) => ({ key, state: i === 0 ? "active" : "pending", detail: "" }));
}

export function useChat(productNames: () => string[]) {
  const turns = ref<Turn[]>([]);
  let controller: AbortController | null = null;
  let nextId = 1;

  const current = computed(() => turns.value.at(-1) ?? null);
  const busy = computed(() => !!current.value && ["working", "answering"].includes(current.value.phase));
  const awaitingChoice = computed(() => current.value?.phase === "clarify");

  function history(upTo: Turn): HistoryMessage[] {
    const out: HistoryMessage[] = [];
    for (const t of turns.value) {
      if (t === upTo) break;
      if (t.phase !== "done") continue;
      out.push({ role: "user", content: t.question });
      if (t.clarifiedWith && t.clarifyText) {
        out.push({ role: "assistant", content: t.clarifyText }, { role: "user", content: t.clarifiedWith });
      }
      if (t.answer) out.push({ role: "assistant", content: plainAnswer(t.answer).slice(0, 8000) });
    }
    return out.slice(-HISTORY_MAX);
  }

  function onProgress(turn: Turn, step: string, detail: string) {
    const at = STEP_KEYS.indexOf(step as StepKey);
    if (at < 0) {
      const active = turn.steps.find(s => s.state === "active");
      if (active && detail) active.detail = detail;
      return;
    }
    turn.steps.forEach((s, i) => {
      if (i < at) s.state = "done";
      else if (i === at) { s.state = "active"; if (detail) s.detail = detail; }
    });
  }

  /** "2 match your question: BellaBot and BellaBot Pro" quando le scelte sono prodotti. */
  function matchSummary(options: string[]): string {
    const names = new Set(productNames().map(n => n.toLowerCase()));
    const products = options.filter(o => names.has(o.toLowerCase()));
    if (products.length < 2) return "";
    const list = products.length === 2 ? products.join(" and ") : `${products.slice(0, -1).join(", ")} and ${products.at(-1)}`;
    return `${products.length} match your question: ${list}`;
  }

  async function run(turn: Turn, message: string, past: HistoryMessage[]) {
    controller?.abort();
    const ctrl = new AbortController();
    controller = ctrl;
    try {
      for await (const ev of streamChat({ message, history: past }, ctrl.signal)) {
        if (ev.event === "progress") onProgress(turn, ev.data.step, ev.data.detail);
        else if (ev.event === "sources") {
          turn.citations = ev.data.citations;
          // una richiesta di chiarimento non ha fonti: i passi restano visibili
          if (turn.citations.length) { turn.phase = "answering"; turn.steps.forEach(s => (s.state = "done")); }
        } else if (ev.event === "token") {
          turn.answer += ev.data.text;
        } else if (ev.event === "done") {
          turn.done = ev.data;
          if (ev.data.status === "needs_clarification" && ev.data.options?.length) {
            const [question, ...rest] = turn.answer.trim().split("\n");
            turn.clarify = { question: question.trim(), detail: rest.join(" ").trim(), options: ev.data.options, text: turn.answer.trim() };
            turn.clarifyText = turn.answer.trim();
            turn.steps[0].state = "done";
            turn.steps[0].detail = matchSummary(ev.data.options) || turn.steps[0].detail;
            turn.steps.slice(1).forEach(s => (s.state = "pending"));
            turn.answer = "";
            turn.phase = "clarify";
          } else {
            turn.steps.forEach(s => (s.state = "done"));
            turn.phase = "done";
          }
        } else if (ev.event === "error") {
          turn.error = ev.data.message;
          turn.phase = "error";
        }
      }
      if (turn.phase === "working" || turn.phase === "answering") turn.phase = "done";
    } catch (err) {
      if (ctrl.signal.aborted) {
        turn.phase = "stopped";
        turn.steps.forEach(s => { if (s.state === "active") s.state = "pending"; });   // lo spinner si ferma
      }
      else { turn.error = err instanceof Error ? err.message : String(err); turn.phase = "error"; }
    } finally {
      if (controller === ctrl) controller = null;
    }
  }

  function ask(question: string) {
    const q = question.trim();
    if (!q || busy.value) return;
    if (current.value?.phase === "clarify") current.value.phase = "stopped";
    const turn = reactive<Turn>({
      id: nextId++, question: q, clarifiedWith: null, clarifyText: null, phase: "working",
      steps: freshSteps(), answer: "", citations: [], done: null, clarify: null, error: null,
    }) as Turn;
    turns.value.push(turn);
    void run(turn, q, history(turn));
  }

  /** Risposta al chiarimento: lo stesso turno riprende con la scelta. */
  function choose(option: string) {
    const turn = current.value;
    if (!turn || turn.phase !== "clarify" || !turn.clarify) return;
    const past = [...history(turn), { role: "user" as const, content: turn.question },
                  { role: "assistant" as const, content: turn.clarify.text }];
    turn.clarifiedWith = option.trim();
    turn.clarify = null;
    turn.phase = "working";
    turn.steps[0].state = "done";
    turn.steps[1].state = "active";
    void run(turn, option.trim(), past);
  }

  function retry(turn: Turn) {
    if (busy.value) return;
    Object.assign(turn, { phase: "working", steps: freshSteps(), answer: "", citations: [], done: null, error: null });
    const past = history(turn);
    if (turn.clarifiedWith && turn.clarifyText) {
      past.push({ role: "user", content: turn.question }, { role: "assistant", content: turn.clarifyText });
    }
    void run(turn, turn.clarifiedWith ?? turn.question, past);
  }

  function stop() {
    if (controller) controller.abort();
    else if (current.value?.phase === "clarify") current.value.phase = "stopped";
  }

  function reset() {
    controller?.abort();
    turns.value = [];
  }

  return { turns, current, busy, awaitingChoice, ask, choose, retry, stop, reset };
}

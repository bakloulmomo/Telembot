// Tipi e chiamate dell'API del backend (backend/README.md).

export type Lang = "en" | "de" | "it";

export interface FigureLabel { n: string | null; text: string }
export interface Figure { id: string | null; url: string; caption: string | null; labels: FigureLabel[] }

export interface Citation {
  n: number;
  label: string;
  text: string;
  product_id: string | null;
  product_name: string | null;
  lang: Lang | null;
  section_id: string | null;
  section_title: string | null;
  page: number | null;
  score: number | null;
  source_url: string | null;
  pdf_url: string | null;
  image_urls: string[];
  figures: Figure[];
  note: string | null;
}

export interface Done {
  answer_id: string;
  products: string[];
  latency_ms: number;
  status?: "answered" | "not_in_docs" | "needs_clarification" | null;
  language?: string | null;
  gaps?: string[];
  options?: string[];
}

export interface Progress { step: string; detail: string }

export interface SourceSection {
  product_id: string;
  product_name: string;
  lang: Lang;
  requested_lang: Lang;
  is_fallback: boolean;
  key: string;
  number: string | null;
  title: string;
  page: number | null;
  page_end: number | null;
  pdf_page: number | null;
  pdf_url: string | null;
  pdf_side: "left" | "right" | null;
  pdf_file: string | null;
  manual_title: string;
  category: "robot" | "accessory";
  parent_number: string | null;
  parent_title: string | null;
  markdown: string;
  image_urls: string[];
}

export interface ProductSummary { id: string; name: string; category: "robot" | "accessory" }

export interface HistoryMessage { role: "user" | "assistant"; content: string }

export type ChatEvent =
  | { event: "progress"; data: Progress }
  | { event: "sources"; data: { citations: Citation[] } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: Done }
  | { event: "error"; data: { code: string; message: string } };

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(url, { signal });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json() as Promise<T>;
}

export const getProducts = () => getJson<ProductSummary[]>("/api/products");

const sourceCache = new Map<string, Promise<SourceSection>>();
export function getSource(url: string): Promise<SourceSection> {
  if (!sourceCache.has(url)) {
    const p = getJson<SourceSection>(url);
    p.catch(() => sourceCache.delete(url));
    sourceCache.set(url, p);
  }
  return sourceCache.get(url)!;
}

/** POST /api/chat letto come flusso di eventi SSE. */
export async function* streamChat(
  body: { message: string; history: HistoryMessage[]; lang?: Lang | "auto"; product_ids?: string[] },
  signal: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ lang: "auto", ...body }),
    signal,
  });
  if (!r.ok || !r.body) {
    let message = `The server answered ${r.status}.`;
    try {
      const err = await r.json();
      if (typeof err.detail === "string") message = err.detail;
    } catch { /* corpo non JSON */ }
    throw new Error(message);
  }
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let cut: number;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      let event = "message", data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) yield { event, data: JSON.parse(data) } as ChatEvent;
    }
  }
}

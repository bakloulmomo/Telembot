// Dal testo della risposta ("… 4.5 hours [1]. Plug it in … [2]") a blocchi e frasi con le loro citazioni.

export interface Inline { text: string; bold: boolean }
export interface Segment { lead: string; parts: Inline[]; cites: number[]; plain: string }
export interface Block { kind: "p" | "li"; segments: Segment[]; cites: number[] }
export interface ParsedAnswer { blocks: Block[]; layout: "prose" | "numbered" }

const LIST_RE = /^\s*(?:[-*•]|\d+[.)])\s+(.*)$/;
const HEADING_RE = /^\s*#{1,6}\s+(.*)$/;
// uno o più marcatori [n], con la punteggiatura che li segue ("hours [1][2].")
const CITES_RE = /((?:\s*\[\d+\])+)([.,;:!?)]*)/g;

function inline(text: string): Inline[] {
  const parts: Inline[] = [];
  const re = /\*\*(.+?)\*\*/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    if (m.index! > last) parts.push({ text: text.slice(last, m.index), bold: false });
    parts.push({ text: m[1], bold: true });
    last = m.index! + m[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), bold: false });
  return parts;
}

function segments(text: string): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  for (const m of text.matchAll(CITES_RE)) {
    const raw = text.slice(last, m.index) + m[2];
    const body = raw.trimStart();
    const cites = [...m[1].matchAll(/\d+/g)].map(x => Number(x[0]));
    out.push({ lead: raw.slice(0, raw.length - body.length), parts: inline(body), cites: [...new Set(cites)], plain: body });
    last = m.index! + m[0].length;
  }
  const rest = text.slice(last);
  if (rest.trim()) out.push({ lead: "", parts: inline(rest), cites: [], plain: rest });
  return out;
}

export function parseAnswer(answer: string): ParsedAnswer {
  const blocks: Block[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) blocks.push(block("p", para.join(" ")));
    para = [];
  };
  for (const raw of answer.split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) { flush(); continue; }
    const li = LIST_RE.exec(line);
    if (li) { flush(); blocks.push(block("li", li[1])); continue; }
    const h = HEADING_RE.exec(line);
    para.push(h ? `**${h[1]}**` : line.trim());
  }
  flush();
  const items = blocks.filter(b => b.kind === "li").length;
  return { blocks, layout: items >= 2 && items >= blocks.length - 1 ? "numbered" : "prose" };
}

function block(kind: Block["kind"], text: string): Block {
  const segs = segments(text);
  return { kind, segments: segs, cites: [...new Set(segs.flatMap(s => s.cites))] };
}

/** Le frasi della risposta che citano la fonte n: servono a trovare il passaggio nel manuale. */
export function sentencesFor(answer: string, n: number): string[] {
  return parseAnswer(answer).blocks.flatMap(b => {
    // in un elenco la fonte vale per tutto il punto ("**T300 § 2.3** [2]: 1 Indicator light…")
    if (b.kind === "li" && b.cites.includes(n)) return [b.segments.map(s => s.plain).join(" ")];
    return b.segments.filter(s => s.cites.includes(n)).map(s => s.plain);
  });
}

/** Testo senza marcatori, per la cronologia inviata al motore. */
export function plainAnswer(answer: string): string {
  return answer.replace(/\s*\[\d+\]/g, "").trim();
}

// La sezione del manuale nel pannello della fonte: blocchi, passaggio evidenziato, "Bullet 2 of 4".

import MarkdownIt from "markdown-it";

// html: false → l'HTML nel Markdown viene mostrato come testo, mai eseguito
const md = new MarkdownIt({ html: false, linkify: false, breaks: false });

export type BlockKind = "heading" | "label" | "li" | "p" | "table";
export interface PassageBlock {
  kind: BlockKind;
  html: string;
  text: string;
  group: number;        // liste e paragrafi consecutivi
  index: number;        // posizione nel gruppo, da 1
  size: number;         // elementi nel gruppo
}

const IMAGE_RE = /^\s*!\[/;
const FIGURE_NOTE_RE = /^\s*>\s*\*?(Figure description|Abbildungsbeschreibung|Descrizione della figura)/i;
const LABELS_RE = /^\s*\*(Labels|Beschriftungen|Etichette):?\*:?\s*$/i;
const LIST_RE = /^\s*(?:[-*•]|\d+[.)])\s+(.*)$/;
const HEADING_RE = /^\s*#{1,6}\s+(.*)$/;
const LABEL_RE = /^\s*(?:\*\*([^*]{1,60})\*\*:?|([A-ZÄÖÜ][\p{L} ]{1,40}):)\s*$/u;

export function splitSection(markdown: string): PassageBlock[] {
  const raw: { kind: BlockKind; text: string; legend?: boolean }[] = [];
  let para: string[] = [];
  let table: string[] = [];
  let skipLegend = false;
  const flushPara = () => { if (para.length) raw.push({ kind: "p", text: para.join(" ") }); para = []; };
  const flushTable = () => { if (table.length) raw.push({ kind: "table", text: table.join("\n") }); table = []; };

  for (const line of markdown.split("\n")) {
    if (!line.trim()) { flushPara(); flushTable(); continue; }
    if (line.trim().startsWith("|")) { flushPara(); table.push(line.trim()); continue; }
    flushTable();
    if (IMAGE_RE.test(line) || FIGURE_NOTE_RE.test(line)) { flushPara(); continue; }
    if (LABELS_RE.test(line)) { flushPara(); skipLegend = true; continue; }
    const li = LIST_RE.exec(line);
    if (skipLegend && li) { raw.push({ kind: "li", text: li[1], legend: true }); continue; }   // legenda di una figura
    skipLegend = false;
    const h = HEADING_RE.exec(line);
    if (h) { flushPara(); raw.push({ kind: "heading", text: h[1] }); continue; }
    if (li) { flushPara(); raw.push({ kind: "li", text: li[1] }); continue; }
    const label = LABEL_RE.exec(line);
    if (label) { flushPara(); raw.push({ kind: "label", text: label[1] ?? label[2] }); continue; }
    if (/^\s+\S/.test(line) && raw.at(-1)?.kind === "li" && !para.length) {
      raw.at(-1)!.text += " " + line.trim();  // continuazione di un punto elenco
      continue;
    }
    para.push(line.trim().replace(/^>\s?/, ""));
  }
  flushPara();
  flushTable();
  // la legenda è già sotto la figura: resta solo se la sezione non ha altro testo
  const content = raw.filter(b => !b.legend && b.kind !== "heading" && b.kind !== "label");
  if (content.length) for (let i = raw.length - 1; i >= 0; i--) if (raw[i].legend) raw.splice(i, 1);

  // gruppi: punti elenco consecutivi, paragrafi della sezione
  const blocks: PassageBlock[] = [];
  let group = 0;
  raw.forEach((b, i) => {
    if (i === 0 || b.kind !== raw[i - 1].kind || b.kind === "table") group++;
    const html = b.kind === "table" ? md.render(b.text) : md.renderInline(b.text);
    blocks.push({ kind: b.kind, html, text: b.text.replace(/\*\*|__|`/g, ""), group, index: 0, size: 0 });
  });
  for (const b of blocks) {
    const same = blocks.filter(x => x.group === b.group);
    b.size = same.length;
    b.index = same.indexOf(b) + 1;
  }
  return blocks;
}

// --- passaggio da evidenziare ----------------------------------------------------

const STOP = new Set(("the and for with that this from are was were has have can will not you your its into when "
  + "then than also only should must may might been more most such each which what where how does "
  + "der die das und mit von für ist sind nicht wenn dann den dem des ein eine einer auf aus bei "
  + "che con per del della delle dei gli una uno non sono come quando più nel nella alla allo").split(" "));

function tokens(text: string): Map<string, number> {
  const out = new Map<string, number>();
  for (const t of text.toLowerCase().match(/[\p{L}\p{N}]+(?:[.,]\d+)?/gu) ?? []) {
    const digit = /\d/.test(t);
    if ((t.length < 3 && !digit) || STOP.has(t)) continue;
    out.set(!digit && t.length > 4 && t.endsWith("s") ? t.slice(0, -1) : t, digit ? 2 : 1);   // chargers → charger
  }
  return out;
}

const norm = (s: string) => s.toLowerCase().replace(/[*_`|>#]/g, " ").replace(/\s+/g, " ").trim();

/**
 * Blocchi che corrispondono a ciò che la risposta dice citando questa fonte.
 * `sentences`: frasi della risposta con [n]; `chunk`: testo della fonte inviato dal motore.
 */
export function findPassage(blocks: PassageBlock[], sentences: string[], chunk: string): number[] {
  const candidates = blocks.map((b, i) => ({ b, i })).filter(({ b }) => b.kind === "li" || b.kind === "p" || b.kind === "table");
  const picked = new Set<number>();

  for (const sentence of sentences) {
    const q = tokens(sentence);
    const scores = candidates.map(({ b, i }) => {
      let s = 0;
      for (const [t] of tokens(b.text)) s += q.get(t) ?? 0;
      return { i, s };
    });
    const best = Math.max(0, ...scores.map(x => x.s));
    if (best < 3) continue;
    scores.filter(x => x.s >= best * 0.8).sort((a, b) => b.s - a.s).slice(0, 2).forEach(x => picked.add(x.i));
  }

  // fonte breve (un pezzo di sezione): i blocchi che contiene sono il passaggio
  const c = norm(chunk);
  const sectionLength = blocks.reduce((n, b) => n + b.text.length, 0);
  if (!picked.size && c.length > 40 && c.length < sectionLength * 0.5) {
    for (const { b, i } of candidates) if (norm(b.text).length > 20 && c.includes(norm(b.text))) picked.add(i);
  }
  return [...picked].sort((a, b) => a - b);
}

/** "Solution, bullets 1–2 of 4", "Bullet 2 of 4", "Paragraph 1 of 3"; null se non è chiaro. */
export function describePassage(blocks: PassageBlock[], picked: number[]): string | null {
  if (!picked.length) return null;
  const first = blocks[picked[0]];
  if (!picked.every(i => blocks[i].group === first.group)) return null;
  if (first.kind === "table") return "Table";
  const nums = picked.map(i => blocks[i].index);
  const contiguous = nums.every((v, k) => k === 0 || v === nums[k - 1] + 1);
  const range = nums.length === 1 ? `${nums[0]}` : contiguous ? `${nums[0]}–${nums.at(-1)}` : nums.join(", ");
  const noun = first.kind === "li" ? "bullet" : "paragraph";
  const what = `${noun}${nums.length > 1 ? "s" : ""} ${range} of ${first.size}`;
  // titoletto subito prima del gruppo, es. "Solution"
  const start = picked[0] - (first.index - 1);
  const before = blocks[start - 1];
  const label = before && (before.kind === "label" || before.kind === "heading") ? before.text : null;
  return label ? `${label}, ${what}` : what[0].toUpperCase() + what.slice(1);
}

/** Blocchi da mostrare: un po' di contesto intorno al passaggio. */
export function passageWindow(blocks: PassageBlock[], picked: number[]): [number, number] {
  if (!picked.length) return [0, Math.min(blocks.length, 5)];
  const first = picked[0], last = picked.at(-1)!;
  const start = Math.max(0, first - (blocks[first - 1]?.kind === "label" ? 2 : 1));
  return [start, Math.min(blocks.length, Math.max(last + 3, start + 4))];
}

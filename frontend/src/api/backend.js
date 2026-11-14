// The real backend (backend/README.md): products, sections of the manuals, comparison.
// Turns its data into the shapes the components read (see DATA.md in the design handoff).


async function getJson(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

// ---------- top bar ----------
export async function loadCounts() {
  const products = await getJson('/api/products')
  const robots = products.filter((p) => p.category === 'robot').length
  return { text: `${products.length} manuals · ${robots} robots and ${products.length - robots} accessories`, products }
}

// ---------- sources panel ----------
const sourceCache = new Map()
export function loadSource(url) {
  if (!sourceCache.has(url)) {
    const p = getJson(url)
    p.catch(() => sourceCache.delete(url))
    sourceCache.set(url, p)
  }
  return sourceCache.get(url)
}

const IMAGE_RE = /^!\[/
const AI_NOTE_RE = /^>\s*\*?(Figure description|Abbildungsbeschreibung|Descrizione della figura)/i
const LEGEND_RE = /^\*(Labels|Beschriftungen|Etichette):?\*:?$/i
const LIST_RE = /^(?:[-*•]|\d+[.)])\s+(.*)$/
const HEADING_RE = /^#{1,6}\s+(.*)$/
const SUB_RE = /^\*\*([^*]{1,60})\*\*:?$/
const plain = (s) => s.replace(/\*\*|__|`/g, '').trim()

/**
 * The section of the manual as snapshot lines: { type: 'li' | 'p' | 'sub' | 'row', text, cells }.
 * The AI figure descriptions are never shown as manual text; a figure legend stays only when
 * the section has no other text (a parts list such as "5 Lidar").
 */
export function snapshotLines(markdown = '') {
  const out = []
  let para = []
  let legend = false
  let header = true                     // first row of a table = its header
  const flush = () => { if (para.length) out.push({ type: 'p', text: plain(para.join(' ')) }); para = [] }

  for (const raw of markdown.split('\n')) {
    const l = raw.trim()
    if (!l) { flush(); header = true; continue }
    if (l.startsWith('|')) {
      flush()
      if (/^\|?\s*:?-{2,}/.test(l)) continue
      const cells = l.split('|').map((c) => plain(c)).filter(Boolean)
      if (header) { header = false; continue }
      if (cells.length >= 2) out.push({ type: 'row', cells: [cells[0], cells.slice(1).join(' · ')] })
      continue
    }
    header = true
    if (IMAGE_RE.test(l) || AI_NOTE_RE.test(l)) { flush(); continue }
    if (LEGEND_RE.test(l)) { flush(); legend = true; continue }
    const li = LIST_RE.exec(l)
    if (legend && li) { out.push({ type: 'li', text: plain(li[1]), legend: true }); continue }
    legend = false
    const h = HEADING_RE.exec(l) || SUB_RE.exec(l)
    if (h) { flush(); out.push({ type: 'sub', text: plain(h[1]) }); continue }
    if (li) { flush(); out.push({ type: 'li', text: plain(li[1]) }); continue }
    para.push(l.replace(/^>\s?/, ''))
  }
  flush()
  const content = out.filter((x) => !x.legend && x.type !== 'sub')
  return content.length ? out.filter((x) => !x.legend) : out
}

/** "4. Troubleshooting › 4.3 Charging Failure" */
export function sectionPath(s) {
  const own = s.number ? `${s.number} ${s.title}` : s.title
  if (s.parent_title) return `${s.parent_number}. ${s.parent_title} › ${own}`
  return s.number && !s.number.includes('.') ? `${s.number}. ${s.title}` : own
}

/** PDF page of a figure from its file name: images/en-p004R-fig02.png → 4 */
export const figurePdfPage = (url) => Number(/-p0*(\d+)[LR]?-fig/i.exec(url || '')?.[1]) || null

/** Citation from /api/chat + section from /api/sources → what the Sources panel shows. */
export function panelCitation(c, s) {
  const lines = s ? snapshotLines(s.markdown) : []
  const heading = s ? (s.number ? `${s.number} ${s.title}` : s.title) : c.section_title
  // leading sub-heading ("Solution") goes under the heading, like in the manual
  const subheading = lines[0]?.type === 'sub' ? lines.shift().text : undefined
  const document = s?.manual_title || (c.product_name ? `${c.product_name} User Manual` : c.label)
  return {
    ...c,
    document,
    family: (s?.category ?? c.category) === 'accessory' ? 'Accessories' : 'Robots',
    lang: s?.lang ?? c.lang,
    section_path: s ? sectionPath(s) : [c.section_id, c.section_title].filter(Boolean).join(' '),
    page: s?.page ?? c.page,
    pdf_page: s?.pdf_page ?? null,
    page_side: s?.pdf_side ?? null,
    pdf_url: s?.pdf_url ?? c.pdf_url,
    pdf_file: s?.pdf_file ?? (c.pdf_url ? decodeURIComponent(c.pdf_url.split('/').pop().split('#')[0]) : ''),
    snapshot: lines.length || heading
      ? { kind: 'mixed', heading, subheading, lines, height: lines.length <= 3 ? 236 : 344, cut: true }
      : null,
    figures: (c.figures || []).map((f) => {
      const pdf = figurePdfPage(f.url)
      return { url: f.url, page: pdf ?? c.page, caption: [heading, pdf && `PDF page ${pdf}`].filter(Boolean).join(', ') }
    }),
  }
}

// ---------- comparison table (03c), when the engine sends none ----------
// The design shows a few rows in plain words (DESIGN-SPEC 1.10), not the whole specification sheet.
const COMPARE_ROWS = ['min_width', 'battery_life', 'charging_time', 'trays', 'tray_load', 'cleaning_width',
  'water_tank', 'productivity', 'speed', 'battery_capacity', 'weight']
const PLAIN_LABELS = { min_width: 'Narrowest aisle', battery_life: 'Runs on one charge', charging_time: 'Time to charge',
  trays: 'Trays', tray_load: 'Load per tray' }
const MAX_ROWS = 6

export async function loadComparison(productIds, citations, lang = 'en') {
  const ids = [...new Set(productIds)].slice(0, 4)
  if (ids.length < 2) return null
  const data = await getJson(`/api/compare?ids=${ids.map(encodeURIComponent).join(',')}&lang=${lang}`)
  const sourceOf = (id) => citations.find((c) => c.product_id === id)?.n ?? null
  return {
    products: data.products.map((p) => ({ id: p.id, name: p.name, n: sourceOf(p.id) })),
    recommended: [],
    rows: data.rows
      .filter((r) => COMPARE_ROWS.includes(r.key))
      .sort((x, y) => COMPARE_ROWS.indexOf(x.key) - COMPARE_ROWS.indexOf(y.key))
      .slice(0, MAX_ROWS)
      .map((r) => ({ label: (lang === 'en' && PLAIN_LABELS[r.key]) || r.label, values: r.values })),
  }
}

// Turns the answer text with [n] markers into paragraphs of claims.
// "Sentence one. [1] Sentence two. [2][3]" → [{ text: 'Sentence one.', ns: [1] }, { text: 'Sentence two.', ns: [2, 3] }]
// The engine may write "hours [1].", Markdown lists and bold, or leave tags such as [FIGURE t300:it:p030R-fig01]:
// the design shows plain prose with the number after the claim, "hours. [1]".
export function normalizeAnswer(text = '') {
  return text
    .replace(/\s*\[(?!\d+\])[^\]\n]*\]/g, '')
    .replace(/\*\*|__/g, '')
    .replace(/^\s*#{1,6}\s+/gm, '')
    .replace(/^(\s*(?:[-*•]|\d+[.)])\s+.*?[^.!?:;\]])((?:\s*\[\d+\])*)\s*$/gm, '$1.$2')   // list item → sentence
    .replace(/^\s*(?:[-*•]|\d+[.)])\s+/gm, '')
    .replace(/((?:\s*\[\d+\])+)([.,;:!?]+)/g, '$2$1')
    .split(/\n\s*\n/)
    .map((p) => p.replace(/\s*\n\s*/g, ' '))
    .join('\n\n')
}

export function parseAnswer(text = '') {
  let index = 0
  return normalizeAnswer(text)
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((para) => {
      const claims = []
      const re = /([^[\]]+?)\s*((?:\[\d+\]\s*)+)/g
      let last = 0
      let m
      while ((m = re.exec(para))) {
        const ns = [...m[2].matchAll(/\[(\d+)\]/g)].map((x) => Number(x[1]))
        claims.push({ index: index++, text: m[1].trim(), ns })
        last = re.lastIndex
      }
      const rest = para.slice(last).trim()
      if (rest) claims.push({ index: index++, text: rest, ns: [] })
      return claims
    })
}

// Splits a citation's raw section text into snapshot lines (used with the live backend).
export function snapshotFromText(text = '') {
  const rows = []
  const lines = []
  for (const raw of text.split('\n')) {
    const l = raw.trim()
    if (!l || /^\|?\s*-{3,}/.test(l) || /^#+\s/.test(l) || /^\*Page/.test(l)) continue
    if (l.startsWith('|')) {
      const cells = l.split('|').map((c) => c.trim()).filter(Boolean)
      if (cells.length >= 2 && cells[0] !== 'Feature') rows.push([cells[0], cells.slice(1).join(' · ')])
      continue
    }
    if (l.startsWith('>') || l.startsWith('![')) continue // never show AI figure descriptions as manual text
    lines.push(l.replace(/^[-*]\s+/, ''))
  }
  return rows.length >= lines.length ? { kind: 'table', lines: rows } : { kind: 'bullets', lines }
}

// Picks the snapshot line that shares the most words with the claim (fallback when the backend sends no cited_lines).
// Common words do not count, "charges" matches "Charging", and a value printed in the manual ("4.5") counts double.
const STOP = new Set('the and for with that this from are was were has have can will not you your its into when then than also only should must may might been more such each which what where does'.split(' '))
const stem = (w) => (/^[a-z]{6,}$/.test(w) ? w.slice(0, 5) : w)
const words = (t) => (t.toLowerCase().match(/[\p{L}0-9.%–-]{2,}/gu) || [])
  .map((w) => w.replace(/[.,]$/, '')).filter((w) => (w.length >= 3 || /\d/.test(w)) && !STOP.has(w)).map(stem)

export function guessCitedLines(lines, claimText) {
  if (!claimText || !lines?.length) return []
  const claim = new Set(words(claimText))
  let best = -1
  let bestScore = 0
  lines.forEach((line, i) => {
    const t = Array.isArray(line) ? line.join(' ') : line
    const score = [...new Set(words(t).filter((w) => claim.has(w)))].reduce((n, w) => n + (/\d/.test(w) ? 2 : 1), 0)
    if (score > bestScore) { bestScore = score; best = i }
  })
  return best >= 0 && bestScore >= 2 ? [best] : []
}

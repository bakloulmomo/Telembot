// Conversation state for the whole app, on the real backend: /api/chat (server-sent events).
// There is no mock data: every answer comes from the RAG engine through the backend.
import { reactive } from 'vue'
import { parseAnswer, snapshotFromText } from './parse.js'
import { withTransition } from './motion.js'
import { groupChats, loadChats, saveChats, serializeTurns } from './chats.js'

const STEP = {
  searching: (detail) => ({ state: 'active', title: 'Searching 22 manuals', detail }),
  searched: (detail) => ({ state: 'done', title: 'Searched 22 manuals', detail }),
  paused: (question) => ({ state: 'paused', title: 'Paused: waiting for your answer', detail: `Answer “${question}” below to continue` }),
  answered: (choice) => ({ state: 'done', title: 'Your answer', detail: choice }),
  reading: (detail) => ({ state: 'active', title: 'Reading the matching pages', detail }),
  read: () => ({ state: 'done', title: 'Read the matching pages', detail: '' }),
  checking: (detail = '') => ({ state: 'active', title: 'Checking each value against its page', detail }),
  pendingRead: () => ({ state: 'pending', title: 'Reading the matching pages', detail: '' }),
  pendingCheck: () => ({ state: 'pending', title: 'Checking each value against its page', detail: '' }),
}

export const state = reactive({
  live: true,
  turns: [],            // { question, phase, steps, clarification, answer, error, choice }
  selected: null,       // { turn, claim, n }
  drawerOpen: false,
  counts: '',           // "22 manuals · 13 robots and 9 accessories", from /api/products
  products: [],
  chatId: null,
  saved: loadChats(),   // chats kept in this browser (Chats drawer)
})

let controller = null

export const current = () => state.turns[state.turns.length - 1]
export const isBusy = () => ['searching', 'answering'].includes(current()?.phase)

function buildAnswer(src) {
  return {
    ...src,
    paragraphs: parseAnswer(src.text),
    shortParts: src.short_answer?.text ? parseAnswer(src.short_answer.text)[0] : null,
  }
}

// ---------- top bar and chats drawer ----------
export async function loadCounts() {
  try {
    const products = await (await fetch('/api/products')).json()
    const robots = products.filter((p) => p.category === 'robot').length
    state.products = products
    state.counts = `${products.length} manuals · ${robots} robots and ${products.length - robots} accessories`
  } catch { /* backend not reachable: the top bar stays empty */ }
}

/** Drawer groups in the shape ChatsDrawer reads: { 'Today': [{ q, pinned, id }], 'Past chats': [...] } */
export function chatGroups() {
  return Object.fromEntries(Object.entries(groupChats(state.saved))
    .map(([label, items]) => [label, items.map((c) => ({ id: c.id, q: c.title, pinned: c.pinned }))]))
}

// ChatsDrawer emits the chat title on open and the row object on pin
const findChat = (item) => state.saved.find((c) => (typeof item === 'string' ? c.title === item : c.id === item.id))

export function openChat(item) {
  const chat = findChat(item)
  if (!chat) return
  newChat()
  state.chatId = chat.id
  state.turns = chat.turns.map((t) => reactive({ ...t }))
}

export function togglePin(item) {
  const chat = findChat(item)
  if (chat) { chat.pinned = !chat.pinned; saveChats(state.saved) }
}

function remember() {
  if (!state.turns.length) return
  const now = Date.now()
  let chat = state.saved.find((c) => c.id === state.chatId)
  if (!chat) {
    chat = { id: `c${now}`, title: state.turns[0].question, pinned: false, updatedAt: now, turns: [] }
    state.saved.unshift(chat)
    state.chatId = chat.id
  }
  chat.turns = serializeTurns(state.turns)
  chat.updatedAt = now
  saveChats(state.saved)
}

// ---------- public actions ----------
export function ask(question) {
  const q = question.trim()
  if (!q || isBusy()) return
  if (current()?.phase === 'clarify') current().phase = 'stopped'
  state.selected = null
  state.turns.push(reactive({ question: q, phase: 'searching', steps: [], clarification: null, answer: null, error: null, choice: null }))
  liveAsk(current(), q, history())
}

/** The same turn goes on with the choice: steps Searched · Your answer · Reading (as in the design). */
export function answerClarification(choice) {
  const turn = current()
  const c = choice.trim()
  if (!turn || turn.phase !== 'clarify' || !c) return
  const past = [...history(), { role: 'user', content: turn.question }, { role: 'assistant', content: turn.clarificationText }]
  withTransition(() => {
    turn.phase = 'searching'
    turn.choice = c
    turn.resumeSteps = [turn.steps[0], STEP.answered(c)]
    turn.steps = [...turn.resumeSteps, STEP.reading(''), STEP.pendingCheck()]
  })
  liveAsk(turn, c, past)
}

export function stop() {
  controller?.abort()
  const turn = current()
  if (turn && ['searching', 'answering', 'clarify'].includes(turn.phase)) {
    // the steps stay where they were, greyed out, so the user sees how far it got
    const run = () => {
      turn.steps = turn.steps.map((s) => (s.state === 'done' ? s : { ...s, state: 'stopped', detail: s.state === 'pending' ? '' : s.detail }))
      turn.phase = 'stopped'
    }
    turn.phase === 'clarify' ? withTransition(run) : run()
  }
}

export function newChat() {
  stop()
  state.turns = []
  state.selected = null
  state.chatId = null
}

export function select(turnIndex, claim, n) {
  state.selected = { turn: turnIndex, claim: claim.index, n, text: claim.text }
}
export function selectGap(turnIndex, gapIndex) {
  state.selected = { turn: turnIndex, gap: gapIndex }
}
export function closePanel() { state.selected = null }

/** Earlier turns of this chat, for follow-up questions. */
function history() {
  return state.turns.slice(0, -1).filter((t) => t.phase === 'done').flatMap((t) => [
    { role: 'user', content: t.question },
    ...(t.choice && t.clarificationText ? [{ role: 'assistant', content: t.clarificationText }, { role: 'user', content: t.choice }] : []),
    ...(t.answer?.text ? [{ role: 'assistant', content: t.answer.text.slice(0, 8000) }] : []),
  ]).slice(-10)
}

// ---------- backend (/api/chat, server-sent events) ----------
async function liveAsk(turn, message, past) {
  controller?.abort()
  const ctrl = new AbortController()
  controller = ctrl
  const before = turn.resumeSteps || []
  if (!before.length) turn.steps = [STEP.searching(''), STEP.pendingRead(), STEP.pendingCheck()]
  let text = ''
  let citations = []
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history: past, lang: 'auto', product_ids: [] }),
      signal: ctrl.signal,
    })
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      let i
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2)
        const event = /^event: (.*)$/m.exec(chunk)?.[1]
        const data = JSON.parse(/^data: (.*)$/m.exec(chunk)?.[1] || '{}')
        if (event === 'progress') onProgress(turn, data, before)
        if (event === 'sources') {
          citations = data.citations.map(normalizeCitation)
          if (citations.length) { turn.phase = 'answering'; turn.steps = [...searched(turn, before), STEP.read(), STEP.checking()] }
        }
        if (event === 'token') text += data.text
        if (event === 'error') { turn.phase = 'error'; turn.error = data.message }
        if (event === 'done') onDone(turn, data, text, citations)
      }
    }
    if (['searching', 'answering'].includes(turn.phase)) turn.phase = 'done'
  } catch {
    if (ctrl.signal.aborted) return
    turn.phase = 'error'
    turn.error = 'The answer could not be loaded. Try again.'
  } finally {
    if (controller === ctrl) controller = null
    delete turn.resumeSteps
    if (['done', 'error'].includes(turn.phase)) remember()
  }
}

// first step: "Searching" while it runs; "Searched" (and "Your answer" after a clarification) once done
const searched = (turn, before) => (before.length ? before : [STEP.searched(turn.steps[0]?.detail || '')])

function onProgress(turn, { step, detail }, before) {
  if (step === 'read') turn.steps = [...searched(turn, before), STEP.reading(detail), STEP.pendingCheck()]
  else if (step === 'check') turn.steps = [...searched(turn, before), STEP.read(), STEP.checking(detail)]
  else if (!before.length) turn.steps = [STEP.searching(detail), STEP.pendingRead(), STEP.pendingCheck()]
}

/** "2 match your question: BellaBot and BellaBot Pro" when the choices are products. */
function matchSummary(options) {
  const names = new Set(state.products.map((p) => p.name.toLowerCase()))
  const found = options.filter((o) => names.has(o.toLowerCase()))
  if (found.length < 2) return ''
  const list = found.length === 2 ? found.join(' and ') : `${found.slice(0, -1).join(', ')} and ${found.at(-1)}`
  return `${found.length} match your question: ${list}`
}

/** "Answer for BellaBot · from 4 pages of the BellaBot User Manual" / "Plain answer · 3 robots compared · from 3 manuals" */
function metaLine(style, citations, products) {
  const named = citations.filter((c) => c.product_name)
  const names = [...new Set(named.map((c) => c.product_name))]
  if (!names.length) return ''
  const pages = new Set(named.filter((c) => c.page != null).map((c) => `${c.product_id}:${c.page}`)).size
  const manuals = names.length === 1 ? `the ${names[0]} User Manual` : `${names.length} manuals`
  if (style === 'plain') {
    const robots = products.every((id) => state.products.find((p) => p.id === id)?.category === 'robot')
    return `Plain answer · ${products.length || names.length} ${robots ? 'robots' : 'products'} compared · from ${manuals}`
  }
  const who = names.length <= 2 ? names.join(' and ') : `${names.slice(0, 2).join(', ')} and ${names.length - 2} more`
  return pages ? `Answer for ${who} · from ${pages} page${pages === 1 ? '' : 's'} of ${manuals}` : `Answer for ${who}`
}

const simplify = (t) => t.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim()

function onDone(turn, data, text, citations) {
  if (data.status === 'needs_clarification') {
    const c = data.clarification || {}
    withTransition(() => {
      turn.phase = 'clarify'
      turn.clarificationText = text.trim()
      turn.clarification = {
        question: c.question || text.replace(/\[\d+\]/g, '').trim(),
        reason: c.reason || '',
        options: c.options || (data.options || []).map((label) => ({ label })),
      }
      turn.steps = [STEP.searched(matchSummary(data.options || []) || turn.steps[0]?.detail || ''),
        STEP.paused(turn.clarification.question), STEP.pendingRead(), STEP.pendingCheck()]
    })
    return
  }
  const products = data.products || []
  const style = data.style || (products.length > 1 ? 'plain' : 'technical')
  const notInDocs = data.status === 'not_in_docs'
  const answer = buildAnswer({
    style,
    meta: notInDocs ? '' : metaLine(style, citations, products),
    text: notInDocs ? '' : text,
    short_answer: data.short_answer || null,
    gaps: (data.gaps || []).map((g) => (typeof g === 'string' ? { text: g } : g)).concat(notInDocs ? [{ text }] : []),
    comparison: data.comparison || null,
    citations,
  })
  // the engine sometimes writes a gap in the answer text too: show it once, as the amber sentence
  const gapTexts = new Set(answer.gaps.map((g) => simplify(g.text)))
  answer.paragraphs = answer.paragraphs
    .map((p) => p.filter((c) => c.ns.length || !gapTexts.has(simplify(c.text))))
    .filter((p) => p.length)
  turn.answer = answer
  turn.phase = 'done'
}

function normalizeCitation(c) {
  // the backend sends the manual's own text of the section (no AI figure descriptions) and its location
  const snap = snapshotFromText(c.text || '')
  const heading = [c.section_id, c.section_title].filter(Boolean).join(' ')
  return {
    ...c,
    document: c.document || (c.product_name ? `${c.product_name} User Manual` : c.label),
    family: c.category === 'accessory' ? 'Accessories' : 'Robots',
    section_path: c.section_path || heading,
    snapshot: { ...snap, heading, height: snap.lines.length <= 3 ? 236 : 344, cut: true },
    figures: (c.figures || []).map((f) => ({ url: f.url, caption: f.caption, page: f.page ?? c.page, labels: f.labels })),
    pdf_file: c.pdf_file || (c.pdf_url ? decodeURIComponent(c.pdf_url.split('/').pop().split('#')[0]) : ''),
  }
}

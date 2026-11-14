// Conversation state for the whole app.
// Live backend (/api/chat, server-sent events) by default. Mock data with ?mock=1 or ?screen=…
// (the designer's prototype mode, to compare each screen with the PNGs in the design handoff).
import { reactive } from 'vue'
import { SPEC, RECO, pickScenario } from './mock.js'
import { parseAnswer } from './parse.js'
import { loadComparison } from './backend.js'
import { groupChats, loadChats, saveChats, serializeTurns } from './chats.js'

const params = new URLSearchParams(location.search)
export const MOCK = params.has('mock') || params.has('screen')
const LIVE = !MOCK

const STEP = {
  searching: (detail) => ({ state: 'active', title: 'Searching 22 manuals', detail }),
  searched: (detail) => ({ state: 'done', title: 'Searched 22 manuals', detail }),
  paused: (question) => ({ state: 'paused', title: 'Paused: waiting for your answer', detail: `Answer “${question}” below to continue` }),
  answered: (choice) => ({ state: 'done', title: 'Your answer', detail: choice }),
  reading: (detail) => ({ state: 'active', title: 'Reading the matching pages', detail }),
  read: (detail = '') => ({ state: 'done', title: 'Read the matching pages', detail }),
  checking: (detail = '') => ({ state: 'active', title: 'Checking each value against its page', detail }),
  pendingRead: () => ({ state: 'pending', title: 'Reading the matching pages', detail: '' }),
  pendingCheck: () => ({ state: 'pending', title: 'Checking each value against its page', detail: '' }),
}

const MOCK_CHATS = {
  'Today': [
    { id: 'm1', q: 'How long does BellaBot charge, and what does it cost?', pinned: false },
    { id: 'm2', q: 'Which robot fits 60 cm aisles?', pinned: false },
    { id: 'm3', q: 'Where is the BellaBot Pro emergency stop?', pinned: false },
  ],
  'Past chats': [
    { id: 'm4', q: 'Max load of the T300', pinned: true },
    { id: 'm5', q: 'CC1 minimal travel width', pinned: false },
    { id: 'm6', q: 'Charging Station Light flashes yellow', pinned: false },
  ],
}

export const state = reactive({
  live: LIVE,
  turns: [],            // { question, phase, steps, clarification, answer, error, choice }
  selected: null,       // { turn, claim, n, text }
  drawerOpen: false,
  products: [],         // from /api/products, for names in the clarification card
  chatId: null,
  saved: LIVE ? loadChats() : [],
  mockChats: MOCK_CHATS,
})

export function chatGroups() {
  if (!LIVE) return state.mockChats
  return Object.fromEntries(Object.entries(groupChats(state.saved))
    .map(([label, items]) => [label, items.map((c) => ({ id: c.id, q: c.title, pinned: c.pinned }))]))
}

let timers = []
let controller = null
const later = (ms, fn) => timers.push(setTimeout(fn, ms))
const clearTimers = () => { timers.forEach(clearTimeout); timers = [] }

export const current = () => state.turns[state.turns.length - 1]
export const isBusy = () => ['searching', 'answering'].includes(current()?.phase)

function buildAnswer(src) {
  return {
    ...src,
    paragraphs: parseAnswer(src.text),
    shortParts: src.short_answer?.text ? parseAnswer(src.short_answer.text)[0] : null,
  }
}

// ---------- public actions ----------
export function ask(question) {
  const q = question.trim()
  if (!q || isBusy()) return
  clearTimers()
  if (current()?.phase === 'clarify') current().phase = 'stopped'
  state.selected = null
  state.turns.push(reactive({ question: q, phase: 'searching', steps: [], clarification: null, answer: null, error: null, choice: null }))
  LIVE ? liveAsk(current(), q, history()) : mockAsk(current())
}

export function answerClarification(choice) {
  const turn = current()
  const c = choice.trim()
  if (!turn || turn.phase !== 'clarify' || !c) return
  if (!LIVE) return mockResume(turn, c)
  // the same turn goes on with the answer, as in the design (steps: Searched, Your answer, Reading…)
  const past = [...history(), { role: 'user', content: turn.question }, { role: 'assistant', content: turn.clarificationText }]
  turn.choice = c
  turn.clarification = null
  turn.phase = 'searching'
  turn.resumeSteps = [turn.steps[0], STEP.answered(c)]
  turn.steps = [...turn.resumeSteps, STEP.reading(''), STEP.pendingCheck()]
  liveAsk(turn, c, past)
}

export function stop() {
  clearTimers()
  controller?.abort()
  const turn = current()
  if (turn && ['searching', 'answering', 'clarify'].includes(turn.phase)) turn.phase = 'stopped'
}

export function newChat() {
  stop()
  state.turns = []
  state.selected = null
  state.chatId = null
}

export function openChat(id) {
  if (!LIVE) { newChat(); const c = Object.values(state.mockChats).flat().find((x) => x.id === id); if (c) ask(c.q); return }
  const chat = state.saved.find((c) => c.id === id)
  if (!chat) return
  newChat()
  state.chatId = chat.id
  state.turns = chat.turns.map((t) => reactive({ ...t }))
}

export function togglePin(id) {
  if (!LIVE) { const c = Object.values(state.mockChats).flat().find((x) => x.id === id); if (c) c.pinned = !c.pinned; return }
  const chat = state.saved.find((c) => c.id === id)
  if (chat) { chat.pinned = !chat.pinned; saveChats(state.saved) }
}

export function select(turnIndex, claim, n) {
  state.selected = { turn: turnIndex, claim: claim.index, n, text: claim.text }
}
export function closePanel() { state.selected = null }

/** Earlier turns of this chat, for the engine (follow-up questions). */
function history() {
  return state.turns.slice(0, -1).filter((t) => t.phase === 'done').flatMap((t) => [
    { role: 'user', content: t.question },
    ...(t.choice && t.clarificationText ? [{ role: 'assistant', content: t.clarificationText }, { role: 'user', content: t.choice }] : []),
    ...(t.answer?.text ? [{ role: 'assistant', content: t.answer.text.slice(0, 8000) }] : []),
  ]).slice(-10)
}

function remember() {
  if (!LIVE || !state.turns.length) return
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

// ---------- mock flow (designer's prototype; timings only drive the states, there are no animations yet) ----------
function mockAsk(turn) {
  const sc = pickScenario(turn.question)
  turn.scenario = sc.id
  turn.steps = [STEP.searching(sc.progress[0].detail), STEP.pendingRead(), STEP.pendingCheck()]
  later(1200, () => { turn.steps[0] = STEP.searching(sc.progress[1].detail) })
  later(2400, () => {
    if (sc.clarification) {
      turn.phase = 'clarify'
      turn.clarification = sc.clarification
      turn.steps = [STEP.searched(sc.searchedDetail), STEP.paused(sc.clarification.question), STEP.pendingRead(), STEP.pendingCheck()]
    } else {
      mockRead(turn, sc, [STEP.searched('4 delivery robots match your question')])
    }
  })
}

function mockResume(turn, choice) {
  const sc = turn.scenario === 'reco' ? RECO : SPEC
  turn.phase = 'searching'
  turn.choice = choice
  mockRead(turn, sc, [STEP.searched(sc.searchedDetail), STEP.answered(choice)])
}

function mockRead(turn, sc, doneSteps) {
  const first = sc.answer.citations[0]
  turn.steps = [...doneSteps, STEP.reading(`${first.document} · ${first.section_title}, p. ${first.page}`), STEP.pendingCheck()]
  later(1400, () => { turn.steps = [...doneSteps, STEP.read(), STEP.checking()] })
  later(2400, () => { turn.answer = buildAnswer(sc.answer); turn.phase = 'done' })
}

// Jump straight to a designed screen (prototype controls, mock mode only).
export function jump(screen) {
  clearTimers()
  state.selected = null
  state.drawerOpen = screen === '00'
  state.turns = []
  if (screen === '00' || screen === '01') return
  const sc = screen === '03c' ? RECO : SPEC
  const turn = reactive({ question: sc.question, scenario: sc.id, phase: 'searching', steps: [], clarification: null, answer: null })
  state.turns.push(turn)
  if (screen === '01.5') {
    turn.steps = [STEP.searching(sc.progress[1].detail), STEP.pendingRead(), STEP.pendingCheck()]
  } else if (screen === '02') {
    turn.phase = 'clarify'
    turn.clarification = sc.clarification
    turn.steps = [STEP.searched(sc.searchedDetail), STEP.paused(sc.clarification.question), STEP.pendingRead(), STEP.pendingCheck()]
  } else {
    turn.phase = 'done'
    turn.answer = buildAnswer(sc.answer)
    const claims = turn.answer.paragraphs.flat()
    if (screen === '04a') select(0, claims[1], 2)
    if (screen === '04b') select(0, claims[3], 3)
  }
}

// ---------- live backend (/api/chat, server-sent events) ----------
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
    if (!res.ok || !res.body) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`)
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
          citations = data.citations
          if (citations.length) { turn.phase = 'answering'; turn.steps = [...searchedSteps(turn, before), STEP.read(), STEP.checking()] }
        }
        if (event === 'token') text += data.text
        if (event === 'error') { turn.phase = 'error'; turn.error = data.message }
        if (event === 'done') await onDone(turn, data, text, citations)
      }
    }
    if (['searching', 'answering'].includes(turn.phase)) turn.phase = 'done'
  } catch (e) {
    if (ctrl.signal.aborted) return
    turn.phase = 'error'
    turn.error = 'The answer could not be loaded. Try again.'
  } finally {
    if (controller === ctrl) controller = null
    delete turn.resumeSteps
    if (['done', 'error'].includes(turn.phase)) remember()
  }
}

// before a clarification: one "Searching" step; after it: Searched + Your answer
function searchedSteps(turn, before) {
  return before.length ? before : [STEP.searched(turn.steps[0]?.detail || '')]
}

function onProgress(turn, { step, detail }, before) {
  if (step === 'read') turn.steps = [...searchedSteps(turn, before), STEP.reading(detail), STEP.pendingCheck()]
  else if (step === 'check') turn.steps = [...searchedSteps(turn, before), STEP.read(), STEP.checking(detail)]
  else if (!before.length) turn.steps = [STEP.searching(detail), STEP.pendingRead(), STEP.pendingCheck()]
}

const simplify = (t) => t.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim()

/** "2 match your question: BellaBot and BellaBot Pro" when the choices are products. */
function matchSummary(options) {
  const names = new Set(state.products.map((p) => p.name.toLowerCase()))
  const found = options.filter((o) => names.has(o.toLowerCase()))
  if (found.length < 2) return ''
  const list = found.length === 2 ? found.join(' and ') : `${found.slice(0, -1).join(', ')} and ${found.at(-1)}`
  return `${found.length} match your question: ${list}`
}

function optionDetail(label) {
  if (state.products.some((p) => p.name.toLowerCase() === label.toLowerCase())) return `${label} User Manual`
  if (/compar|confront|vergleich/i.test(label)) return 'Side by side, each value with its source'
  return ''
}

/** "Answer for BellaBot · from 4 pages of the BellaBot User Manual" / "Plain answer · 4 robots compared · from 4 manuals" */
function metaLine(style, citations, products) {
  const named = citations.filter((c) => c.product_name)
  const names = [...new Set(named.map((c) => c.product_name))]
  if (!names.length) return ''
  const pages = new Set(named.filter((c) => c.page != null).map((c) => `${c.product_id}:${c.page}`)).size
  const manuals = names.length === 1 ? `the ${names[0]} User Manual` : `${names.length} manuals`
  if (style === 'plain') {
    const robots = products.length && products.every((id) => state.products.find((p) => p.id === id)?.category === 'robot')
    return `Plain answer · ${products.length || names.length} ${robots ? 'robots' : 'products'} compared · from ${manuals}`
  }
  const who = names.length <= 2 ? names.join(' and ') : `${names.slice(0, 2).join(', ')} and ${names.length - 2} more`
  return pages ? `Answer for ${who} · from ${pages} page${pages === 1 ? '' : 's'} of ${manuals}` : `Answer for ${who}`
}

async function onDone(turn, data, text, citations) {
  if (data.status === 'needs_clarification') {
    const c = data.clarification || {}
    const [first, ...rest] = text.replace(/\s*\[\d+\]/g, '').trim().split('\n')
    turn.phase = 'clarify'
    turn.clarificationText = text.trim()
    turn.clarification = {
      question: c.question || first.trim(),
      reason: c.reason || rest.join(' ').trim(),
      options: c.options || (data.options || []).map((label) => ({ label, detail: optionDetail(label) })),
    }
    turn.steps = [STEP.searched(matchSummary(data.options || []) || turn.steps[0]?.detail || ''),
      STEP.paused(turn.clarification.question), STEP.pendingRead(), STEP.pendingCheck()]
    return
  }
  const products = data.products || []
  const style = data.style || (products.length > 1 ? 'plain' : 'technical')
  const notInDocs = data.status === 'not_in_docs'
  const answer = {
    style,
    meta: notInDocs ? '' : metaLine(style, citations, products),
    text: notInDocs ? '' : text,
    short_answer: data.short_answer || null,
    gaps: (data.gaps || []).map((g) => (typeof g === 'string' ? { text: g } : g)).concat(notInDocs ? [{ text }] : []),
    comparison: data.comparison || null,
    citations,
  }
  if (style === 'plain' && !answer.comparison && products.length > 1) {
    const lang = ['en', 'de', 'it'].includes(data.language) ? data.language : 'en'
    answer.comparison = await loadComparison(products, citations, lang).catch(() => null)
  }
  const built = buildAnswer(answer)
  // the engine sometimes also writes a gap in the answer text: show it once, in amber
  const gapTexts = new Set(built.gaps.map((g) => simplify(g.text)))
  built.paragraphs = built.paragraphs
    .map((p) => p.filter((c) => c.ns.length || !gapTexts.has(simplify(c.text))))
    .filter((p) => p.length)
  // plain answers: the first sentence is the headline when the engine sends no short answer (DATA.md),
  // if it is short enough to read as one
  if (style === 'plain' && !built.short_answer && built.paragraphs[0]?.[0]?.text.length <= 140) {
    const head = built.paragraphs[0].shift()
    if (!built.paragraphs[0].length) built.paragraphs.shift()
    built.short_answer = { headline: head.text, ns: head.ns }
  }
  turn.answer = built
  turn.phase = 'done'
}

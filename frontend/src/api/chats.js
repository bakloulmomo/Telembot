// Past chats for the Chats drawer (00), kept in this browser only.
// Every read and write is guarded: private windows or blocked storage just mean no history.

const KEY = 'telembot.chats.v2'
const MAX = 30
// v1 could hold answers of the old fake engine: drop it
try { localStorage.removeItem('telembot.chats.v1') } catch { /* storage blocked */ }

export function loadChats() {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

export function saveChats(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)))
  } catch {
    /* storage full or blocked: the chat stays in memory */
  }
}

/** Only what is needed to show a finished chat again (no in-flight state). */
export function serializeTurns(turns) {
  return JSON.parse(JSON.stringify(turns.map((t) => ({
    question: t.question,
    choice: t.choice ?? null,
    clarificationText: t.clarificationText ?? null,
    phase: ['done', 'error'].includes(t.phase) ? t.phase : 'stopped',
    steps: [],
    clarification: null,
    answer: t.answer,
    error: t.error ?? null,
  }))))
}

/** Drawer groups: "Today" and "Past chats", pinned first (the drawer sorts them). */
export function groupChats(list) {
  const today = new Date().toDateString()
  const groups = { 'Today': [], 'Past chats': [] }
  for (const c of [...list].sort((a, b) => b.updatedAt - a.updatedAt)) {
    groups[new Date(c.updatedAt).toDateString() === today ? 'Today' : 'Past chats'].push(c)
  }
  return Object.fromEntries(Object.entries(groups).filter(([, items]) => items.length))
}

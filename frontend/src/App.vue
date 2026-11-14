<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import TopBar from './components/TopBar.vue'
import ChatsDrawer from './components/ChatsDrawer.vue'
import HomeView from './components/HomeView.vue'
import Turn from './components/Turn.vue'
import PromptBar from './components/PromptBar.vue'
import ClarificationCard from './components/ClarificationCard.vue'
import SourcePanel from './components/SourcePanel.vue'
import PrototypeControls from './components/PrototypeControls.vue'
import { COUNTS } from './api/mock.js'
import { loadCounts } from './api/backend.js'
import {
  MOCK, state, ask, answerClarification, stop, newChat, openChat, togglePin, chatGroups,
  select, closePanel, jump, current,
} from './api/useChat.js'

// "Prototype" bar: only in mock mode (?mock=1 or ?screen=…), and hidden with ?clean=1
const showControls = MOCK && !new URLSearchParams(location.search).has('clean')
const scroller = ref(null)
const counts = ref(COUNTS)

const last = computed(() => current())
const busy = computed(() => ['searching', 'answering'].includes(last.value?.phase))
const clarifying = computed(() => last.value?.phase === 'clarify')
const groups = computed(() => chatGroups())

const panel = computed(() => {
  const sel = state.selected
  if (!sel) return null
  const turn = state.turns[sel.turn]
  const citation = turn?.answer?.citations?.find((c) => c.n === sel.n)
  if (!citation) return null
  const cited = turn.answer.claim_lines?.[`${sel.claim}:${sel.n}`] ?? null
  return { citation, cited, claimText: sel.text }
})

const onSelect = (ti, claim) => select(ti, claim, claim.ns[0])

// a new question scrolls so that it sits at the top of the thread (y 124)
watch(() => state.turns.length, async () => {
  await nextTick()
  const el = scroller.value
  const lastTurn = el?.querySelector('.thread')?.lastElementChild
  if (el && lastTurn) el.scrollTo({ top: Math.max(0, lastTurn.offsetTop - 40) })
})

const onKey = (e) => {
  if (e.key !== 'Escape') return
  if (state.selected) closePanel()
  else if (state.drawerOpen) state.drawerOpen = false
}
onMounted(async () => {
  window.addEventListener('keydown', onKey)
  const screen = new URLSearchParams(location.search).get('screen')   // e.g. ?screen=04a opens that Figma screen
  if (screen) jump(screen)
  if (!MOCK) {
    try {
      const { text, products } = await loadCounts()
      counts.value = text
      state.products = products
    } catch { /* backend not reachable: keep the default counts */ }
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="app">
    <ChatsDrawer
      v-if="state.drawerOpen" :groups="groups" :active-id="state.chatId"
      @close="state.drawerOpen = false" @new-chat="newChat" @open="openChat" @pin="togglePin"
    />

    <main class="main">
      <TopBar :show-brand="!state.drawerOpen" :counts="counts" @open-chats="state.drawerOpen = true" />

      <HomeView v-if="!state.turns.length" @ask="ask" />

      <template v-else>
        <div ref="scroller" class="scroller">
          <div class="column thread">
            <Turn
              v-for="(t, i) in state.turns" :key="i" :turn="t"
              :selected-claim="state.selected?.turn === i ? state.selected.claim : null"
              @select="onSelect(i, $event)"
            />
          </div>
        </div>
        <div class="bottom">
          <div class="column">
            <ClarificationCard
              v-if="clarifying" :clarification="last.clarification"
              @choose="answerClarification" @stop="stop"
            />
            <PromptBar v-else :mode="busy ? 'busy' : 'idle'" @submit="ask" @stop="stop" />
          </div>
        </div>
      </template>
    </main>

    <SourcePanel
      v-if="panel" :citation="panel.citation" :cited="panel.cited" :claim-text="panel.claimText"
      @close="closePanel"
    />

    <PrototypeControls v-if="showControls" :live="state.live" @jump="jump" />
  </div>
</template>

<style scoped>
.app { display: flex; height: 100vh; min-width: 1100px; overflow: hidden; }
.main { position: relative; flex: 1; min-width: 0; display: flex; flex-direction: column; }
.column { width: var(--column-width); max-width: calc(100% - 48px); margin: 0 auto; }
.scroller { flex: 1; overflow-y: auto; }
/* thread starts at y 124 = top bar 84 + 40; bottom space keeps the last line above the bottom bar */
.thread { display: flex; flex-direction: column; gap: 64px; padding: 40px 0 360px; }
.bottom { position: absolute; left: 0; right: 0; bottom: var(--bottom-gap); z-index: 2; }  /* above the comparison cells (z-index 1) */
</style>

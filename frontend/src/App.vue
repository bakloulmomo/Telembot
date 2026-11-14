<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import TopBar from './components/TopBar.vue'
import ChatsDrawer from './components/ChatsDrawer.vue'
import HomeView from './components/HomeView.vue'
import Turn from './components/Turn.vue'
import PromptBar from './components/PromptBar.vue'
import ClarificationCard from './components/ClarificationCard.vue'
import SourcePanel from './components/SourcePanel.vue'
import {
  state, ask, answerClarification, stop, newChat, select, selectGap, closePanel, current,
  loadCounts, chatGroups, openChat, togglePin,
} from './api/useChat.js'
import { withTransition, motionOn } from './api/motion.js'

// Home → conversation: the composer text becomes the question title, the composer becomes the prompt bar.
const askFromHome = (q) => withTransition(() => ask(q))
const home = ref(null)
const scroller = ref(null)
const groups = computed(() => chatGroups())

const last = computed(() => current())
const busy = computed(() => ['searching', 'answering'].includes(last.value?.phase))
const clarifying = computed(() => last.value?.phase === 'clarify')

const panel = computed(() => {
  const sel = state.selected
  if (!sel) return null
  const turn = state.turns[sel.turn]
  if (sel.gap != null) {
    const gap = turn?.answer?.gaps?.[sel.gap]
    return gap ? { gap, key: `gap-${sel.gap}` } : null
  }
  const citation = turn?.answer?.citations?.find((c) => c.n === sel.n)
  if (!citation) return null
  const cited = turn.answer.claim_lines?.[`${sel.claim}:${sel.n}`] ?? null
  return { citation, cited, claimText: sel.text }
})

// keep the last panel content while the panel slides out
const shownPanel = ref(null)
watch(panel, (v) => { if (v) shownPanel.value = v }, { immediate: true })

const onSelect = (ti, claim) => select(ti, claim, claim.ns[0])

// a new question scrolls so that it sits at the top of the thread (y 124)
watch(() => state.turns.length, async () => {
  await nextTick()
  const el = scroller.value
  const lastTurn = el?.querySelector('.thread')?.lastElementChild
  if (el && lastTurn) el.scrollTo({ top: Math.max(0, lastTurn.offsetTop - 40), behavior: motionOn() ? 'smooth' : 'auto' })
})

const onKey = (e) => {
  if (e.key !== 'Escape') return
  if (state.selected) closePanel()
  else if (state.drawerOpen) state.drawerOpen = false
}
onMounted(() => {
  window.addEventListener('keydown', onKey)
  loadCounts()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="app">
    <!-- panels push the page: their slot grows from 0, the page area shrinks with it (320 ms in, 240 ms out) -->
    <Transition name="push">
      <div v-if="state.drawerOpen" class="slot slot--left">
        <ChatsDrawer
          :groups="groups" :active-question="state.turns[0]?.question || ''"
          @close="state.drawerOpen = false" @new-chat="newChat" @open="openChat" @pin="togglePin"
        />
      </div>
    </Transition>

    <main class="main">
      <TopBar :show-brand="!state.drawerOpen" :counts="state.counts" @open-chats="state.drawerOpen = true" />

      <HomeView v-if="!state.turns.length" ref="home" @ask="askFromHome" />

      <template v-else>
        <div ref="scroller" class="scroller">
          <div class="column thread">
            <Turn
              v-for="(t, i) in state.turns" :key="i" :turn="t" :first="i === 0"
              :selected-claim="state.selected?.turn === i && state.selected.gap == null ? state.selected.claim : null"
              :selected-gap="state.selected?.turn === i ? state.selected.gap ?? null : null"
              @select-gap="selectGap(i, $event)"
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

    <Transition name="push">
      <div v-if="panel" class="slot slot--right">
        <SourcePanel
          :citation="shownPanel.citation" :gap="shownPanel.gap" :cited="shownPanel.cited" :claim-text="shownPanel.claimText || shownPanel.key"
          @close="closePanel"
        />
      </div>
    </Transition>

  </div>
</template>

<style scoped>
/* window height on every screen (dvh: also on phones, where 100vh is taller than the visible area) */
.app { display: flex; height: 100vh; height: 100dvh; overflow: hidden; }
.main { position: relative; flex: 1; min-width: 0; display: flex; flex-direction: column; }
.column { width: var(--column-width); max-width: calc(100% - 48px); margin: 0 auto; }
.scroller { flex: 1; overflow-y: auto; }
/* thread starts at y 124 = top bar 84 + 40; bottom space keeps the last line above the bottom bar */
.thread { display: flex; flex-direction: column; gap: 64px; padding: 40px 0 360px; }
.bottom { position: absolute; left: 0; right: 0; bottom: var(--bottom-gap); z-index: 1; }
/* page-colored fade behind the bottom bar: the answer scrolls under it instead of being cut */
.bottom::before {
  content: ""; position: absolute; left: 0; right: 0; bottom: calc(-1 * var(--bottom-gap));
  height: calc(100% + var(--bottom-gap) + 40px); z-index: -1; pointer-events: none;
  background: linear-gradient(to bottom, rgba(254, 254, 252, 0), var(--color-bg-page) 45%);
}
.slot { flex: none; height: 100%; display: flex; position: relative; z-index: 2; }  /* above the page so the sheet shadow shows */
.push-enter-active.slot, .push-leave-active.slot { overflow: hidden; }
.slot--left { width: 300px; justify-content: flex-end; }    /* the drawer's right edge enters first: it comes from the left */
.slot--right { width: var(--panel-width); justify-content: flex-start; } /* the panel's left edge enters first: it comes from the right */

/* Narrower than 1100 there is no room to push the page (DESIGN-SPEC is drawn at 1440):
   the drawer and the Sources panel lie over the page instead, still full window height. */
@media (max-width: 1099px) {
  .slot { position: fixed; top: 0; bottom: 0; height: auto; z-index: 20; }
  .slot--left { left: 0; width: min(300px, 100vw); }
  .slot--right { right: 0; width: min(var(--panel-width), 100vw); }
}
@media (max-width: 640px) {
  .column { max-width: calc(100% - 32px); }
}
</style>

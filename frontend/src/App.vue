<script setup lang="ts">
// Telembot: domanda (01), ricerca (01.5), chiarimento (02), risposta (03a/b), fonte (04a/b).
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ClarifyCard from "./components/ClarifyCard.vue";
import Composer from "./components/Composer.vue";
import SourcePanel from "./components/SourcePanel.vue";
import TurnView from "./components/TurnView.vue";
import { useChat } from "./composables/useChat";
import { getProducts, type ProductSummary } from "./lib/api";

const products = ref<ProductSummary[]>([]);
const names = computed(() => products.value.map(p => p.name));
const robots = computed(() => products.value.filter(p => p.category === "robot").length);
const manuals = computed(() => products.value.length || 22);

const chat = useChat(() => names.value);
const { turns, current, busy } = chat;

// fonte aperta nel pannello: turno e numero
const open = ref<{ turnId: number; n: number } | null>(null);
const openTurn = computed(() => turns.value.find(t => t.id === open.value?.turnId) ?? null);
const openCitation = computed(() => openTurn.value?.citations.find(c => c.n === open.value?.n) ?? null);

const thread = ref<HTMLElement | null>(null);
const homeComposer = ref<InstanceType<typeof Composer> | null>(null);
const dockComposer = ref<InstanceType<typeof Composer> | null>(null);

onMounted(async () => {
  try { products.value = await getProducts(); } catch { /* il backend non risponde: l'intestazione resta generica */ }
  window.addEventListener("keydown", onKey);
});
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && open.value) { open.value = null; return; }
  if (e.key === "Escape" && busy.value) chat.stop();
}

/** Prima domanda: il campo scende dal centro al fondo (come in ChatGPT). */
async function ask(text: string) {
  const from = !turns.value.length ? homeComposer.value?.root?.getBoundingClientRect() : null;
  chat.ask(text);
  await nextTick();
  const to = dockComposer.value?.root;
  if (from && to) {
    const rect = to.getBoundingClientRect();
    to.animate(
      [{ transform: `translateY(${from.top - rect.top}px)`, opacity: 0.6 }, { transform: "none", opacity: 1 }],
      { duration: 450, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)" },
    );
  }
  scrollToLast();
}

function scrollToLast() {
  void nextTick(() => {
    const el = thread.value?.querySelector<HTMLElement>(".turn:last-of-type");
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function choose(option: string) { chat.choose(option); scrollToLast(); }

function newChat() {
  open.value = null;
  chat.reset();
  void nextTick(() => homeComposer.value?.focus());
}

function openSource(turnId: number, n: number) {
  open.value = open.value?.turnId === turnId && open.value.n === n ? null : { turnId, n };
}

// mentre la risposta arriva, la pagina segue il testo se si è già in fondo
watch(() => current.value?.answer.length, () => {
  const el = thread.value;
  if (!el || current.value?.phase !== "answering") return;
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 160) el.scrollTop = el.scrollHeight;
});

const headline = computed(() => products.value.length
  ? `${products.value.length} manuals · ${robots.value} robots and ${products.value.length - robots.value} accessories`
  : "PUDU manuals");
</script>

<template>
  <div class="app" :class="{ 'panel-open': !!openCitation }">
    <main class="main">
      <header class="bar">
        <button type="button" class="brand" aria-label="Telembot, new chat" @click="newChat">Telembot</button>
        <span class="count">{{ headline }}</span>
      </header>

      <Transition name="home" mode="out-in">
        <!-- 01 · Ask -->
        <section v-if="!turns.length" key="home" class="hero">
          <h1>What do you need to know?</h1>
          <p>Answers from the PUDU manuals, with the page they come from.</p>
          <div class="column">
            <Composer ref="homeComposer" variant="home" placeholder="Ask anything about PUDU robots and accessories" autofocus @send="ask" />
          </div>
        </section>

        <div v-else key="thread" class="thread-wrap">
          <div ref="thread" class="thread">
            <div class="column">
              <TurnView
                v-for="(t, i) in turns" :key="t.id" :turn="t" :manuals="manuals" :is-last="i === turns.length - 1"
                :open-n="open?.turnId === t.id ? open.n : null" @open="openSource(t.id, $event)" @retry="chat.retry(t)"
              />
            </div>
          </div>
          <div class="dock-bar">
            <div class="column">
              <Transition name="dock" mode="out-in">
                <ClarifyCard
                  v-if="current?.phase === 'clarify' && current.clarify" key="clarify" :clarify="current.clarify"
                  :product-names="names" @choose="choose" @stop="chat.stop()"
                />
                <Composer
                  v-else key="dock" ref="dockComposer" variant="dock" placeholder="Ask a follow-up" :busy="busy"
                  @send="ask" @stop="chat.stop()"
                />
              </Transition>
            </div>
          </div>
        </div>
      </Transition>
    </main>

    <div class="aside" :class="{ open: !!openCitation }">
      <Transition name="panel">
        <SourcePanel
          v-if="openCitation && openTurn" :key="open!.turnId" :citation="openCitation" :answer="openTurn.answer"
          @close="open = null"
        />
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.app { display: flex; height: 100dvh; overflow: hidden; }
.main { position: relative; flex: 1; min-width: 0; display: flex; flex-direction: column; }

.bar { flex: none; height: 84px; display: flex; align-items: center; justify-content: space-between; padding: 0 41px 0 40px; }
.brand { border: 0; background: none; padding: 0; font-size: 19px; font-weight: 600; letter-spacing: -0.02em; }
.count { font-size: 14.5px; color: var(--muted); white-space: nowrap; }

.column { width: 100%; max-width: var(--column); margin: 0 auto; }

/* 01 · Ask */
.hero { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0 16px 166px; text-align: center; }
.hero h1 { margin: 0; font-size: 34px; line-height: 42px; font-weight: 500; letter-spacing: -0.025em; }
.hero p { margin: 10px 0 41px; font-size: 18px; color: var(--muted); }
.hero .column { text-align: left; }
.hero h1, .hero p { animation: fade-up .5s var(--ease) both; }
.hero p { animation-delay: .06s; }
.hero .column { animation: fade-up .5s var(--ease) .12s both; }

/* conversazione */
.thread-wrap { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.thread { flex: 1; overflow-y: auto; padding: 0 16px; scroll-behavior: smooth; scrollbar-gutter: stable; }
.dock-bar { position: relative; flex: none; padding: 0 16px 40px; }
.dock-bar::before { /* il testo sfuma sotto il campo */
  content: ""; position: absolute; left: 0; right: 0; bottom: 100%; height: 40px; pointer-events: none;
  background: linear-gradient(to bottom, rgb(253 253 252 / 0), var(--bg));
}

/* pannello della fonte: entra da destra, la conversazione si sposta */
.aside { flex: none; width: 0; height: 100%; overflow: hidden; transition: width .38s var(--ease); }
.aside.open { width: var(--panel); }
.panel-enter-active, .panel-leave-active { transition: transform .38s var(--ease), opacity .3s ease; }
.panel-enter-from, .panel-leave-to { transform: translateX(40px); opacity: 0; }

.home-leave-active { transition: opacity .2s ease, transform .25s var(--ease); }
.home-leave-to { opacity: 0; transform: translateY(-12px); }
.home-enter-active { transition: opacity .3s ease; }
.home-enter-from { opacity: 0; }
.dock-enter-active, .dock-leave-active { transition: opacity .2s ease, transform .25s var(--ease); }
.dock-enter-from, .dock-leave-to { opacity: 0; transform: translateY(10px); }

@media (max-width: 1100px) {
  .aside { position: fixed; inset: 0 0 0 auto; z-index: 10; box-shadow: -20px 0 60px rgb(0 0 0 / .08); }
  .aside.open { width: min(var(--panel), 100vw); }
}
@media (max-width: 640px) {
  .bar { height: 64px; padding: 0 16px; }
  .count { display: none; }
  .hero h1 { font-size: 27px; line-height: 34px; }
  .hero p { font-size: 16px; margin-bottom: 28px; }
  .dock-bar { padding-bottom: 16px; }
}
</style>

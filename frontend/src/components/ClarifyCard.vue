<script setup lang="ts">
// 02 · Clarify: la domanda del motore, le scelte numerate e una risposta libera.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import Composer from "./Composer.vue";
import Icon from "./Icon.vue";
import type { Clarify } from "@/composables/useChat";

const props = defineProps<{ clarify: Clarify; productNames: string[] }>();
const emit = defineEmits<{ choose: [option: string]; stop: [] }>();

const hovered = ref(0);
const COMPARE_RE = /compar|confront|vergleich/i;

const options = computed(() => props.clarify.options.map(label => {
  const isProduct = props.productNames.some(n => n.toLowerCase() === label.toLowerCase());
  const detail = isProduct ? `${label} User Manual` : COMPARE_RE.test(label) ? "Side by side, each value with its source" : "";
  return { label, detail };
}));

// 1, 2, 3… sceglie l'opzione quando non si sta scrivendo
function onKey(e: KeyboardEvent) {
  const target = e.target as HTMLElement | null;
  if (target && ["TEXTAREA", "INPUT"].includes(target.tagName)) return;
  const i = Number(e.key) - 1;
  if (Number.isInteger(i) && i >= 0 && i < options.value.length) { e.preventDefault(); emit("choose", options.value[i].label); }
}
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <section class="card" aria-labelledby="clarify-title">
    <header class="head">
      <div>
        <h2 id="clarify-title">{{ clarify.question }}</h2>
        <p v-if="clarify.detail">{{ clarify.detail }}</p>
      </div>
      <button type="button" class="stop" @click="emit('stop')">
        <Icon name="stop-circle" :size="17" /> Stop request
      </button>
    </header>

    <ul class="options" @mouseleave="hovered = 0">
      <li v-for="(o, i) in options" :key="o.label" :style="{ animationDelay: `${0.05 * i + 0.1}s` }">
        <button
          type="button" class="option" :class="{ hot: hovered === i, 'before-hot': hovered === i + 1 }"
          @mouseenter="hovered = i" @focus="hovered = i" @click="emit('choose', o.label)"
        >
          <span class="num">{{ i + 1 }}</span>
          <span class="label">
            <span class="name">{{ o.label }}</span>
            <span v-if="o.detail" class="detail">{{ o.detail }}</span>
          </span>
          <Icon name="arrow-right" :size="18" class="go" />
        </button>
      </li>
    </ul>

    <Composer variant="reply" :placeholder="`Type your answer to “${clarify.question}”`" autofocus @send="emit('choose', $event)" />
  </section>
</template>

<style scoped>
.card {
  background: var(--surface); border: 1px solid var(--line); border-radius: 28px; padding: 22px 11px 11px;
  box-shadow: 0 10px 40px rgb(0 0 0 / .05); animation: rise .45s var(--ease) both;
}
@keyframes rise { from { opacity: 0; transform: translateY(24px) scale(.98); } to { opacity: 1; transform: none; } }

.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 0 0 20px 13px; }
h2 { margin: 6px 0 0; font-size: 19px; line-height: 26px; font-weight: 600; letter-spacing: -0.01em; }
.head p { margin: 4px 0 0; font-size: 16px; line-height: 24px; color: var(--text-2); }
.stop {
  display: inline-flex; align-items: center; gap: 8px; flex: none; height: 44px; padding: 0 20px 0 16px;
  border: 0; border-radius: 22px; background: var(--well); font-size: 14.5px; font-weight: 600;
  transition: background-color .2s ease, transform .15s var(--ease);
}
.stop:hover { background: var(--well-strong); }
.stop:active { transform: scale(.97); }

.options { list-style: none; margin: 0 0 12px; padding: 0; }
.options li { animation: fade-up .35s var(--ease) both; }
.option {
  position: relative; display: grid; grid-template-columns: 28px 1fr 20px; align-items: center; column-gap: 16px;
  width: 100%; padding: 14px 13px 14px 12px; border: 0; border-radius: 12px; background: transparent; text-align: left;
  transition: background-color .15s ease;
}
.option::after {
  content: ""; position: absolute; left: 12px; right: 12px; bottom: 0; height: 1px; background: var(--line);
  transition: opacity .15s ease;
}
.options li:last-child .option::after, .option.hot::after, .option.before-hot::after { opacity: 0; }
.option.hot { background: var(--well); }
.num {
  width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid #dcdcda; border-radius: 8px; background: var(--surface); font-size: 13px; color: var(--text-2);
}
.label { display: flex; flex-direction: column; min-width: 0; }
.name { font-size: 19px; line-height: 26px; }
.detail { font-size: 14.5px; line-height: 20px; color: var(--muted); margin-top: 2px; }
.go { opacity: 0; transform: translateX(-6px); transition: opacity .15s ease, transform .2s var(--ease); }
.option.hot .go { opacity: 1; transform: none; }
</style>

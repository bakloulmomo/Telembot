<script setup lang="ts">
// 01.5 · Searching e 02 · Clarify: i tre passi del motore, con il passo in pausa quando serve una risposta.
import { computed } from "vue";
import Icon from "./Icon.vue";
import type { Step } from "@/composables/useChat";

const props = defineProps<{ steps: Step[]; manuals: number; pausedOn?: string | null }>();

const TITLES = {
  search: ["Searching {n} manuals", "Searched {n} manuals"],
  read: ["Reading the matching pages", "Read the matching pages"],
  check: ["Checking each value against its page", "Checked each value against its page"],
} as const;

interface Row { key: string; state: Step["state"]; title: string; detail: string }

const rows = computed<Row[]>(() => {
  const out: Row[] = props.steps.map(s => ({
    key: s.key,
    state: s.state,
    title: TITLES[s.key][s.state === "done" ? 1 : 0].replace("{n}", String(props.manuals)),
    detail: s.state === "active" || s.state === "done" ? s.detail : "",
  }));
  if (props.pausedOn) {
    out.splice(1, 0, {
      key: "paused", state: "paused", title: "Paused: waiting for your answer",
      detail: `Answer “${props.pausedOn}” below to continue`,
    });
  }
  return out;
});
</script>

<template>
  <ol class="steps" aria-live="polite">
    <li v-for="row in rows" :key="row.key" class="step" :class="row.state">
      <span class="icon">
        <Transition name="icon" mode="out-in" :duration="{ enter: 300, leave: 100 }">
          <span v-if="row.state === 'active'" key="a" class="spinner" />
          <Icon v-else-if="row.state === 'done'" key="d" name="check" :size="15" />
          <Icon v-else-if="row.state === 'paused'" key="p" name="pause" :size="18" />
          <span v-else key="o" class="ring" />
        </Transition>
      </span>
      <span class="text">
        <span class="title">{{ row.title }}</span>
        <Transition name="detail" mode="out-in">
          <span v-if="row.detail" :key="row.detail" class="detail">{{ row.detail }}</span>
        </Transition>
      </span>
      <span class="sr-only">{{ row.state === 'done' ? 'done' : row.state === 'active' ? 'in progress' : row.state }}</span>
    </li>
  </ol>
</template>

<style scoped>
.steps { list-style: none; margin: 0 -12px; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.step {
  display: grid; grid-template-columns: 20px 1fr; column-gap: 12px; align-items: start;
  padding: 7px 12px; border-radius: 10px;
  transition: background-color .3s ease, color .3s ease;
  animation: fade-up .35s var(--ease) both;
}
.step:nth-child(2) { animation-delay: .05s; }
.step:nth-child(3) { animation-delay: .1s; }
.step:nth-child(4) { animation-delay: .15s; }

.icon { height: 28px; display: flex; align-items: center; justify-content: center; }
.text { display: flex; flex-direction: column; min-width: 0; }
.title { font-size: 19px; line-height: 28px; transition: color .3s ease; }
.detail { font-size: 14.5px; line-height: 20px; color: var(--muted); margin-top: 2px; }

.active .title { color: var(--text); }
.done .title { color: var(--muted); }
.done .icon { color: #8d8d8d; }
.pending .title { color: var(--faint); }
.paused { background: var(--blue-bg); padding-top: 10px; padding-bottom: 10px; }
.paused .title, .paused .icon { color: var(--blue); }
.paused .detail { color: #4a5568; }

.spinner {
  width: 17px; height: 17px; border-radius: 50%;
  border: 1.8px solid #e3e3e1; border-top-color: var(--text); border-right-color: var(--text);
  animation: spin .8s linear infinite;
}
.ring { width: 17px; height: 17px; border-radius: 50%; border: 1.5px solid #bdbdbb; }

.icon-enter-active { animation: pop .3s var(--ease); }
.icon-leave-active { transition: opacity .1s ease; }
.icon-leave-to { opacity: 0; }
.detail-enter-active, .detail-leave-active { transition: opacity .2s ease, transform .2s var(--ease); }
.detail-enter-from { opacity: 0; transform: translateY(3px); }
.detail-leave-to { opacity: 0; }
</style>

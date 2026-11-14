<script setup lang="ts">
// Un turno: la domanda come titolo, poi i passi (01.5, 02) o la risposta (03a, 03b).
import { computed } from "vue";
import AnswerBody from "./AnswerBody.vue";
import Icon from "./Icon.vue";
import ProgressSteps from "./ProgressSteps.vue";
import type { Turn } from "@/composables/useChat";

const props = defineProps<{ turn: Turn; manuals: number; openN: number | null; isLast: boolean }>();
const emit = defineEmits<{ open: [n: number]; retry: [] }>();

const showSteps = computed(() => ["working", "clarify"].includes(props.turn.phase)
  || (props.turn.phase === "stopped" && !props.turn.answer));
const showAnswer = computed(() => !!props.turn.answer && ["answering", "done", "stopped", "error"].includes(props.turn.phase));

/** "Answer for BellaBot · from 4 pages of the BellaBot User Manual" */
const meta = computed(() => {
  const t = props.turn;
  if (t.phase === "done" && t.done?.status === "not_in_docs") return `Not found in the ${props.manuals} manuals`;
  const cites = t.citations.filter(c => c.product_name);
  if (!cites.length || !showAnswer.value) return null;
  const names = [...new Set(cites.map(c => c.product_name!))];
  const pages = new Set(cites.filter(c => c.page != null).map(c => `${c.product_id}:${c.page}`)).size;
  const forWhat = names.length <= 2 ? names.join(" and ") : `${names.slice(0, 2).join(", ")} and ${names.length - 2} more`;
  const from = names.length === 1 ? `the ${names[0]} User Manual` : `${names.length} manuals`;
  return pages ? `Answer for ${forWhat} · from ${pages} page${pages === 1 ? "" : "s"} of ${from}` : `Answer for ${forWhat}`;
});
</script>

<template>
  <article class="turn" :class="{ last: isLast }">
    <h1 class="question">{{ turn.question }}</h1>
    <p v-if="turn.clarifiedWith" class="chosen"><Icon name="reply" :size="15" /> {{ turn.clarifiedWith }}</p>
    <Transition name="fade"><p v-if="meta" class="meta">{{ meta }}</p></Transition>

    <div class="body">
      <Transition name="steps">
        <div v-if="showSteps" class="working">
          <ProgressSteps :steps="turn.steps" :manuals="manuals" :paused-on="turn.phase === 'clarify' ? turn.clarify?.question : null" />
          <div v-if="turn.phase === 'working'" class="skeleton" aria-hidden="true">
            <span style="width: 100%" /><span style="width: 90%" /><span style="width: 55%" />
          </div>
        </div>
      </Transition>

      <AnswerBody
        v-if="showAnswer" :answer="turn.answer" :citations="turn.citations" :gaps="turn.phase === 'done' ? turn.done?.gaps ?? [] : []"
        :streaming="turn.phase === 'answering'" :open-n="openN" @open="emit('open', $event)"
      />

      <p v-if="turn.phase === 'stopped'" class="notice">
        {{ turn.answer ? "Stopped." : "Request stopped." }}
        <button type="button" class="link" @click="emit('retry')"><Icon name="retry" :size="15" /> Ask again</button>
      </p>
      <p v-if="turn.phase === 'error'" class="notice error" role="alert">
        {{ turn.error }}
        <button type="button" class="link" @click="emit('retry')"><Icon name="retry" :size="15" /> Try again</button>
      </p>
    </div>
  </article>
</template>

<style scoped>
.turn { padding: 36px 0 56px; scroll-margin-top: 0; animation: fade-up .4s var(--ease) both; }
.turn + .turn { border-top: 1px solid #f0f0ee; }
.turn.last { min-height: calc(100dvh - 84px - 120px); }

.question { margin: 0; padding: 0 12px; font-size: 28px; line-height: 36px; font-weight: 500; letter-spacing: -0.022em; overflow-wrap: anywhere; }
.chosen { display: inline-flex; align-items: center; gap: 6px; margin: 10px 12px 0; padding: 4px 12px 4px 10px;
  border-radius: 14px; background: var(--well); font-size: 14.5px; color: var(--text-2); animation: fade-up .3s var(--ease) both; }
.meta { margin: 10px 0 0; padding: 0 12px; font-size: 14.5px; color: var(--muted); }

.body { margin-top: 44px; padding: 0 12px; }
.working { display: flex; flex-direction: column; }

.skeleton { display: flex; flex-direction: column; gap: 16px; margin-top: 52px; }
.skeleton span {
  height: 12px; border-radius: 6px;
  background: linear-gradient(90deg, #f3f3f1 25%, #e9e9e7 37%, #f3f3f1 63%); background-size: 400% 100%;
  animation: shimmer 1.6s ease infinite;
}

.notice { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin: 20px 0 0; font-size: 16px; color: var(--muted); }
.notice.error { color: var(--danger); }
.link { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border: 1px solid var(--line); border-radius: 16px;
  background: var(--surface); color: var(--text); font-size: 14px; font-weight: 500; transition: background-color .2s ease; }
.link:hover { background: var(--well); }

.fade-enter-active { transition: opacity .3s ease; }
.fade-enter-from { opacity: 0; }
.steps-leave-active { transition: opacity .2s ease, transform .25s var(--ease); }
.steps-leave-to { opacity: 0; transform: translateY(-6px); }

@media (max-width: 640px) {
  .turn { padding-top: 24px; }
  .question { font-size: 23px; line-height: 30px; }
  .body { margin-top: 28px; }
}
</style>

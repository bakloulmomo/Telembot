<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import PromptBar from './PromptBar.vue'
const props = defineProps({ clarification: { type: Object, required: true } })
const emit = defineEmits(['choose', 'stop'])
// Keys 1, 2, 3 pick an option (when the focus is not in the text field).
const onKey = (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  const i = Number(e.key) - 1
  const opt = props.clarification.options[i]
  if (opt) emit('choose', opt.label)
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <section class="card squircle" aria-label="The answer needs your input">
    <div class="header">
      <div class="texts">
        <h2 class="t-headline">{{ clarification.question }}</h2>
        <p v-if="clarification.reason" class="t-body-regular reason">{{ clarification.reason }}</p>
      </div>
      <button class="stop squircle" @click="$emit('stop')">
        <span class="stop-square"></span>
        <span class="t-callout-strong">Stop request</span>
      </button>
    </div>
    <div class="options">
      <template v-for="(o, i) in clarification.options" :key="o.label">
        <div v-if="i > 0" class="divider"><span></span></div>
        <button class="option squircle" @click="$emit('choose', o.label)">
          <span class="key t-footnote-medium">{{ i + 1 }}</span>
          <span class="option-texts">
            <span class="t-body-large">{{ o.label }}</span>
            <span v-if="o.detail" class="t-callout-regular detail">{{ o.detail }}</span>
          </span>
          <Icon name="arrow_forward" class="arrow" />
        </button>
      </template>
    </div>
    <PromptBar
      mode="reply"
      :placeholder="`Type your answer to “${clarification.question}”`"
      @submit="$emit('choose', $event)"
    />
  </section>
</template>

<style scoped>
.card {
  width: 100%;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-3xl);
  padding: 12px;
  display: flex; flex-direction: column; gap: 12px;
}
/* 12 card padding + 8 = 20 from the card edge to the Stop button: concentric with radius 42 = 22 + 20 */
.header { display: flex; align-items: flex-start; gap: 24px; padding: 8px 8px 8px 12px; }
.texts { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; padding-top: 8px; }
.reason { color: var(--color-text-secondary); }
.stop {
  flex: none; height: 44px; border-radius: var(--radius-xl);
  padding: 0 20px 0 16px; display: inline-flex; align-items: center; gap: 8px;
  background: var(--color-bg-highlight-subtle); color: var(--color-text-primary);
}
.stop-square { width: 12px; height: 12px; border-radius: 2.5px; background: var(--color-text-highlight); display: block; }
.options { display: flex; flex-direction: column; }
.divider { padding: 2px 12px; }
.divider span { display: block; height: 1px; background: var(--color-border-subtle); }
.option {
  display: flex; align-items: center; gap: 16px; padding: 12px;
  border-radius: var(--radius-md); text-align: left;
}
.key {
  width: 28px; height: 28px; flex: none; border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-subtle); color: var(--color-text-secondary);
  display: flex; align-items: center; justify-content: center;
}
.option-texts { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; color: var(--color-text-primary); }
.detail { color: var(--color-text-secondary); }
.arrow { visibility: hidden; color: var(--color-text-primary); }
.option:hover { background: var(--color-bg-surface); }
.option:hover .key { color: var(--color-text-primary); }
.option:hover .arrow { visibility: visible; }
</style>

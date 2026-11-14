<script setup>
import Icon from './Icon.vue'
import Spinner from './Spinner.vue'
defineProps({ steps: { type: Array, required: true }, skeleton: { type: Boolean, default: false } })
const ICON = { done: 'check', paused: 'pause_circle', pending: 'radio_button_unchecked', stopped: 'stop_circle' }
</script>

<template>
  <div class="progress">
    <ol class="steps" aria-live="polite">
      <li v-for="(s, i) in steps" :key="i" class="step squircle" :class="`is-${s.state}`">
        <span class="status">
          <!-- spinner → check pops in: the step is finished -->
          <Transition name="pop" mode="out-in">
            <Spinner v-if="s.state === 'active'" key="spin" />
            <Icon v-else :key="s.state" :name="ICON[s.state]" />
          </Transition>
        </span>
        <span class="texts">
          <span class="t-body-large title">{{ s.title }}</span>
          <!-- the detail line changes as the system reads another manual / page -->
          <Transition name="swap" mode="out-in">
            <span v-if="s.detail" :key="s.detail" class="t-callout-regular detail">{{ s.detail }}</span>
          </Transition>
        </span>
      </li>
    </ol>
    <div v-if="skeleton" class="skeleton" aria-hidden="true">
      <span style="width: 100%"></span><span style="width: 90%"></span><span style="width: 55%"></span>
    </div>
  </div>
</template>

<style scoped>
.progress { display: flex; flex-direction: column; gap: 40px; }
.steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.step {
  display: flex; gap: 12px; padding: 8px 12px; border-radius: var(--radius-md);
  transition: background-color var(--motion-base) var(--ease-standard);
}
.status { width: 20px; height: 30px; padding-top: 5px; flex: none; display: flex; justify-content: center; }
.texts { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.title, .status { transition: color var(--motion-base) var(--ease-standard); }
.detail { color: var(--color-text-secondary); }

.is-done .status { color: var(--color-text-tertiary); }
.is-done .title { color: var(--color-text-secondary); }
.is-active .title {
  /* slow light passing over the text: work in progress (1.6 s loop) */
  color: transparent;
  background: linear-gradient(90deg, var(--color-text-primary) 0%, var(--color-text-primary) 40%, var(--color-text-tertiary) 50%, var(--color-text-primary) 60%, var(--color-text-primary) 100%);
  background-size: 250% 100%;
  -webkit-background-clip: text; background-clip: text;
  animation: m-shimmer 1.6s linear infinite;
}
.is-paused { background: var(--color-bg-info-subtle); }
.is-paused .status, .is-paused .title { color: var(--color-text-info); }
.is-pending .status, .is-pending .title, .is-pending .detail,
.is-stopped .status, .is-stopped .title, .is-stopped .detail { color: var(--color-text-disabled); }

.skeleton { display: flex; flex-direction: column; gap: 16px; padding: 8px 12px 0; margin-top: -8px; }
.skeleton span {
  display: block; height: 12px; border-radius: 6px; background: var(--color-bg-surface);
  animation: m-pulse 1.4s var(--ease-standard) infinite;   /* the answer is coming */
}
.skeleton span:nth-child(2) { animation-delay: 0.15s; }
.skeleton span:nth-child(3) { animation-delay: 0.3s; }
@media (prefers-reduced-motion: reduce) { .is-active .title { animation: none; color: var(--color-text-primary); background: none; } }
</style>

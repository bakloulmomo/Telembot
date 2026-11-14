<script setup>
import Icon from './Icon.vue'
import Spinner from './Spinner.vue'
defineProps({ steps: { type: Array, required: true }, skeleton: { type: Boolean, default: false } })
</script>

<template>
  <div class="progress">
    <ol class="steps" aria-live="polite">
      <li v-for="(s, i) in steps" :key="i" class="step squircle" :class="`is-${s.state}`">
        <span class="status">
          <Spinner v-if="s.state === 'active'" />
          <Icon v-else-if="s.state === 'done'" name="check" />
          <Icon v-else-if="s.state === 'paused'" name="pause_circle" />
          <Icon v-else name="radio_button_unchecked" />
        </span>
        <span class="texts">
          <span class="t-body-large title">{{ s.title }}</span>
          <span v-if="s.detail" class="t-callout-regular detail">{{ s.detail }}</span>
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
.step { display: flex; gap: 12px; padding: 8px 12px; border-radius: var(--radius-md); }
.status { width: 20px; height: 30px; padding-top: 5px; flex: none; display: flex; justify-content: center; }
.texts { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.detail { color: var(--color-text-secondary); }

.is-done .status { color: var(--color-text-tertiary); }
.is-done .title { color: var(--color-text-secondary); }
.is-active .title { color: var(--color-text-primary); }
.is-paused { background: var(--color-bg-info-subtle); }
.is-paused .status, .is-paused .title { color: var(--color-text-info); }
.is-pending .status, .is-pending .title, .is-pending .detail { color: var(--color-text-disabled); }

.skeleton { display: flex; flex-direction: column; gap: 16px; padding: 8px 12px 0; margin-top: -8px; }
.skeleton span { display: block; height: 12px; border-radius: 6px; background: var(--color-bg-surface); }
</style>

<script setup>
import SourceMarks from './SourceMarks.vue'
defineProps({ answer: { type: Object, required: true } })
</script>

<template>
  <!-- Technical: exact values with units first -->
  <div v-if="answer.style === 'technical'" class="short">
    <div v-if="answer.short_answer?.values?.length" class="values">
      <template v-for="(v, i) in answer.short_answer.values" :key="i">
        <span v-if="i > 0" class="divider" aria-hidden="true"></span>
        <div class="kv">
          <div class="value-row">
            <span class="t-title-large value">{{ v.value }}</span>
            <span class="t-headline unit">{{ v.unit }}</span>
          </div>
          <div class="label-row">
            <span class="t-callout-regular label">{{ v.label }}</span>
            <SourceMarks :ns="[v.n]" :size="16" />
          </div>
        </div>
      </template>
    </div>
    <p v-for="g in answer.gaps.filter((g) => g.topic)" :key="g.topic" class="t-footnote-medium gap">
      {{ g.topic }}: not in the manuals
    </p>
  </div>

  <!-- Plain (non-technical): a plain headline and one sentence -->
  <div v-else class="short plain">
    <p class="t-title-small">{{ answer.short_answer?.headline }}<SourceMarks v-if="answer.short_answer?.ns?.length" :ns="answer.short_answer.ns" /></p>
    <p v-if="answer.shortParts" class="t-body-large sentence">
      <template v-for="(c, i) in answer.shortParts" :key="i">{{ c.text }}<SourceMarks :ns="c.ns" />{{ ' ' }}</template>
    </p>
  </div>
</template>

<style scoped>
.short { display: flex; flex-direction: column; gap: 16px; padding: 0 var(--column-inset); }
.short.plain { gap: 6px; }
.values { display: flex; align-items: center; gap: 28px; }
.divider { width: 1px; height: 56px; background: var(--color-border-subtle); flex: none; }
.kv { display: flex; flex-direction: column; gap: 2px; }
.value-row { display: flex; align-items: baseline; gap: 4px; }
.value { color: var(--color-text-primary); }
.unit { color: var(--color-text-secondary); }
.label-row { display: flex; align-items: center; gap: 6px; }
.label { color: var(--color-text-secondary); }
.label-row :deep(.marks) { line-height: 1; }
.gap { color: var(--color-text-warning); }
.sentence { color: var(--color-text-secondary); }
</style>

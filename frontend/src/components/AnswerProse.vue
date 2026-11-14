<script setup>
// The answer as continuous prose. Each claim ends with its source number(s).
// Hover / selected: surface background behind that sentence only (line by line), underline, number turns black.
import SourceMarks from './SourceMarks.vue'
const props = defineProps({
  paragraphs: { type: Array, required: true },
  gaps: { type: Array, default: () => [] },
  selected: { type: Number, default: null },  // index of the selected claim
})
const emit = defineEmits(['select'])
const open = (claim) => { if (claim.ns.length) emit('select', claim) }
// keep a short first word ("I", "A") on the same line as the next word
const tie = (s) => s.replace(/^(\S{1,2}) /, '$1 ')
</script>

<template>
  <div class="prose">
    <p v-for="(para, pi) in paragraphs" :key="pi" class="t-body-large paragraph">
      <template v-for="c in para" :key="c.index">
        <span
          class="claim"
          :class="{ 'is-selected': c.index === selected, 'is-plain': !c.ns.length }"
          :role="c.ns.length ? 'button' : null"
          :tabindex="c.ns.length ? 0 : null"
          @click="open(c)" @keydown.enter="open(c)"
        ><span class="claim-text">{{ c.text }}</span><SourceMarks :ns="c.ns" /></span>{{ ' ' }}
      </template>
      <template v-if="pi === paragraphs.length - 1">
        <span v-for="g in gaps" :key="g.text" class="gap">{{ tie(g.text) }} </span>
      </template>
    </p>
    <p v-if="!paragraphs.length && gaps.length" class="t-body-large paragraph">
      <span v-for="g in gaps" :key="g.text" class="gap">{{ tie(g.text) }} </span>
    </p>
  </div>
</template>

<style scoped>
.prose { display: flex; flex-direction: column; gap: 20px; padding: 0 var(--column-inset); }
.paragraph { color: var(--color-text-primary); }
.claim {
  cursor: pointer;
  border-radius: var(--radius-sm);
  padding: 3px 6px; margin: 0 -6px;          /* background reaches 6 px past the text, full 30 px line */
  -webkit-box-decoration-break: clone; box-decoration-break: clone;
}
.claim.is-plain { cursor: text; }
.claim:not(.is-plain):hover, .claim.is-selected { background: var(--color-bg-surface); }
.claim:not(.is-plain):hover .claim-text, .claim.is-selected .claim-text {
  text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 4px;
}
.claim:hover :deep(.mark), .claim.is-selected :deep(.mark) { color: var(--color-text-primary); }
/* Unverified part: amber text only, no icon, no background (5:1 on the page background). */
.gap { color: var(--color-text-warning); }
</style>

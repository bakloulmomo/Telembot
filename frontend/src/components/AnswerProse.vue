<script setup>
// The answer as continuous prose. Each claim ends with its source number(s).
// Hover / selected: surface background behind that sentence only (line by line), underline, number turns black.
// Reveal: claims fade in one after the other (60 ms apart), then their source number pops in: the user sees
// that each sentence is backed by a source as it arrives. The unverified part comes last.
import SourceMarks from './SourceMarks.vue'
const props = defineProps({
  paragraphs: { type: Array, required: true },
  gaps: { type: Array, default: () => [] },
  selected: { type: Number, default: null },  // index of the selected claim
  selectedGap: { type: Number, default: null }, // index of the selected unverified part
  delay: { type: Number, default: 0 },        // reveal starts after this many stagger steps
})
const emit = defineEmits(['select', 'select-gap'])
const open = (claim) => { if (claim.ns.length) emit('select', claim) }
// keep a short first word ("I", "A") on the same line as the next word
const tie = (s) => s.replace(/^(\S{1,2}) /, '$1 ')
const total = () => props.paragraphs.flat().length
</script>

<template>
  <div class="prose">
    <p v-for="(para, pi) in paragraphs" :key="pi" class="t-body-large paragraph">
      <template v-for="c in para" :key="c.index">
        <span
          class="claim m-fade"
          :style="{ '--i': delay + c.index }"
          :class="{ 'is-selected': c.index === selected, 'is-plain': !c.ns.length }"
          :role="c.ns.length ? 'button' : null"
          :tabindex="c.ns.length ? 0 : null"
          @click="open(c)" @keydown.enter="open(c)"
        ><span class="claim-text">{{ c.text }}</span><SourceMarks :ns="c.ns" class="m-pop" :style="{ '--i': delay + c.index + 2 }" /></span>{{ ' ' }}
      </template>
      <template v-if="pi === paragraphs.length - 1">
        <template v-for="(g, gi) in gaps" :key="g.text"><span
          class="gap m-fade" :class="{ 'is-selected': gi === selectedGap }" :style="{ '--i': delay + total() + 2 }"
          role="button" tabindex="0" @click="$emit('select-gap', gi)" @keydown.enter="$emit('select-gap', gi)"
        ><span class="claim-text">{{ tie(g.text) }}</span></span>{{ ' ' }}</template>
      </template>
    </p>
    <p v-if="!paragraphs.length && gaps.length" class="t-body-large paragraph">
      <span
        v-for="(g, gi) in gaps" :key="g.text" class="gap m-fade" :class="{ 'is-selected': gi === selectedGap }"
        role="button" tabindex="0" @click="$emit('select-gap', gi)"
      ><span class="claim-text">{{ tie(g.text) }}</span> </span>
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
  transition: background-color var(--motion-fast) var(--ease-standard);
}
.claim-text {
  text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 4px;
  text-decoration-color: transparent;
  transition: text-decoration-color var(--motion-fast) var(--ease-standard);
}
.claim.is-plain { cursor: text; }
.claim:not(.is-plain):hover, .claim.is-selected { background: var(--color-bg-surface); }
.claim:not(.is-plain):hover .claim-text, .claim.is-selected .claim-text { text-decoration-color: currentColor; }
.claim :deep(.mark) { transition: color var(--motion-fast) var(--ease-standard); }
.claim:hover :deep(.mark), .claim.is-selected :deep(.mark) { color: var(--color-text-primary); }
/* Unverified part: amber text only, no icon, no background (5:1 on the page background).
   It behaves like a claim: hover / selected = amber-subtle background + underline; click opens the panel
   in its "Not in the manuals" state. */
.gap {
  color: var(--color-text-warning); cursor: pointer;
  border-radius: var(--radius-sm); padding: 3px 6px; margin: 0 -6px;
  -webkit-box-decoration-break: clone; box-decoration-break: clone;
  transition: background-color var(--motion-fast) var(--ease-standard);
}
.gap:hover, .gap.is-selected { background: var(--color-bg-warning-subtle); }
.gap:hover .claim-text, .gap.is-selected .claim-text { text-decoration-color: currentColor; }
</style>

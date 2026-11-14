<script setup>
import { computed } from 'vue'
import ProgressSteps from './ProgressSteps.vue'
import ShortAnswer from './ShortAnswer.vue'
import AnswerProse from './AnswerProse.vue'
import ComparisonTable from './ComparisonTable.vue'
const props = defineProps({
  turn: { type: Object, required: true },
  selectedClaim: { type: Number, default: null },
})
defineEmits(['select'])
// the short answer block only when it has something to show (values, a gap topic, a headline)
const hasShort = computed(() => {
  const a = props.turn.answer
  if (!a) return false
  if (a.style === 'technical') return !!a.short_answer?.values?.length || a.gaps?.some((g) => g.topic)
  return !!a.short_answer?.headline
})
</script>

<template>
  <article class="turn" :class="{ 'is-answer': turn.phase === 'done' }">
    <header class="question-group">
      <h1 class="t-title-medium question">{{ turn.question }}</h1>
      <p v-if="turn.phase === 'done' && turn.answer?.meta" class="t-callout-regular meta">{{ turn.answer.meta }}</p>
    </header>

    <ProgressSteps
      v-if="['searching', 'answering', 'clarify'].includes(turn.phase)"
      :steps="turn.steps" :skeleton="turn.phase !== 'clarify'"
    />

    <p v-else-if="turn.phase === 'stopped'" class="t-body-large status">You stopped this answer.</p>
    <p v-else-if="turn.phase === 'error'" class="t-body-large status">{{ turn.error }}</p>

    <template v-else-if="turn.phase === 'done' && turn.answer">
      <ShortAnswer v-if="hasShort" :answer="turn.answer" />
      <section v-if="turn.answer.paragraphs.length || turn.answer.gaps.length" class="section">
        <p class="t-overline label">Details</p>
        <AnswerProse
          :paragraphs="turn.answer.paragraphs" :gaps="turn.answer.gaps" :selected="selectedClaim"
          @select="$emit('select', $event)"
        />
      </section>
      <section v-if="turn.answer.comparison" class="section">
        <p class="t-overline label">Comparison</p>
        <ComparisonTable :comparison="turn.answer.comparison" />
      </section>
    </template>
  </article>
</template>

<style scoped>
.turn { display: flex; flex-direction: column; gap: 40px; }
.turn.is-answer { gap: 36px; }
.question-group { display: flex; flex-direction: column; gap: 12px; padding: 0 var(--column-inset); }
.meta, .status { color: var(--color-text-secondary); }
.status { padding: 0 var(--column-inset); }
.section { display: flex; flex-direction: column; gap: 12px; }
.label { color: var(--color-text-tertiary); padding-left: var(--column-inset); }
</style>

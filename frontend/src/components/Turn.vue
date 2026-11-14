<script setup>
import { computed } from 'vue'
import ProgressSteps from './ProgressSteps.vue'
import ShortAnswer from './ShortAnswer.vue'
import AnswerProse from './AnswerProse.vue'
import ComparisonTable from './ComparisonTable.vue'
const props = defineProps({
  turn: { type: Object, required: true },
  selectedClaim: { type: Number, default: null },
  selectedGap: { type: Number, default: null },
  first: { type: Boolean, default: false },   // the first question morphs from the home composer
})
defineEmits(['select', 'select-gap'])
// the short answer block only when it has something to show: values or a gap topic (technical), a headline (plain).
// Without this an empty block adds a second 36 px gap above DETAILS when the engine sends no short answer.
const hasShort = computed(() => {
  const a = props.turn.answer
  if (!a) return false
  if (a.style === 'technical') return !!a.short_answer?.values?.length || !!a.gaps?.some((g) => g.topic)
  return !!a.short_answer?.headline
})
</script>

<template>
  <article class="turn" :class="{ 'is-answer': turn.phase === 'done' }">
    <header class="question-group">
      <h1 class="t-title-medium question" :style="first ? { viewTransitionName: 'question' } : null">{{ turn.question }}</h1>
      <p v-if="turn.phase === 'done' && turn.answer?.meta" class="t-callout-regular meta m-fade">{{ turn.answer.meta }}</p>
    </header>

    <ProgressSteps
      v-if="['searching', 'answering', 'clarify', 'stopped'].includes(turn.phase)"
      :steps="turn.steps" :skeleton="['searching', 'answering'].includes(turn.phase)"
    />
    <p v-if="turn.phase === 'stopped'" class="t-body-large status m-fade">You stopped this answer.</p>
    <p v-else-if="turn.phase === 'error'" class="t-body-large status">{{ turn.error }}</p>

    <!-- the answer arrives in reading order: short answer, then details sentence by sentence, then the table -->
    <template v-if="turn.phase === 'done' && turn.answer">
      <ShortAnswer v-if="hasShort" :answer="turn.answer" />
      <section v-if="turn.answer.paragraphs.length || turn.answer.gaps.length" class="section">
        <p class="t-overline label m-fade" style="--i: 2">Details</p>
        <AnswerProse
          :paragraphs="turn.answer.paragraphs" :gaps="turn.answer.gaps" :selected="selectedClaim" :selected-gap="selectedGap" :delay="3"
          @select="$emit('select', $event)" @select-gap="$emit('select-gap', $event)"
        />
      </section>
      <section v-if="turn.answer.comparison" class="section">
        <p class="t-overline label m-fade" :style="{ '--i': 4 + turn.answer.paragraphs.flat().length }">Comparison</p>
        <!-- on narrow windows the table scrolls sideways instead of squeezing the values -->
        <div class="table-scroll"><ComparisonTable :comparison="turn.answer.comparison" :delay="5 + turn.answer.paragraphs.flat().length" /></div>
      </section>
    </template>
  </article>
</template>

<style scoped>
.turn { display: flex; flex-direction: column; gap: 40px; }
.turn.is-answer { gap: 36px; }
.question-group { display: flex; flex-direction: column; gap: 12px; padding: 0 var(--column-inset); }
.meta, .status { color: var(--color-text-secondary); }
.status { padding: 0 var(--column-inset); margin-top: -24px; }
.section { display: flex; flex-direction: column; gap: 12px; }
.label { color: var(--color-text-tertiary); padding-left: var(--column-inset); }
.table-scroll { overflow-x: auto; }
</style>

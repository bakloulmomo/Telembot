<script setup>
import { ref } from 'vue'
import Composer from './Composer.vue'
import StartingPoint from './StartingPoint.vue'
import { motionOn } from '../api/motion.js'
const emit = defineEmits(['ask'])
const composer = ref(null)
// Clicking an example: the question appears in the field for a moment, then travels up to become the title.
const pick = async (q) => {
  await composer.value.fill(q)
  setTimeout(() => emit('ask', q), motionOn() ? 220 : 0)
}
defineExpose({ pick })
</script>

<template>
  <div class="home">
    <div class="block">
      <h1 class="t-title-large title">What do you need to know?</h1>
      <p class="t-body-large subtitle">Answers from the PUDU manuals, with the page they come from.</p>
      <Composer ref="composer" class="composer" @submit="$emit('ask', $event)" />
      <div class="starts">
        <StartingPoint
          icon="manage_search" title="Look up a spec"
          description="Exact values with units, procedures and fixes."
          :questions="['How long does BellaBot charge?', 'Where is the BellaBot Pro emergency stop?']"
          @pick="pick"
        />
        <StartingPoint
          icon="compare_arrows" title="Find the right robot"
          description="Plain answers and side-by-side comparisons."
          :questions="['Which robot fits 60 cm aisles?', 'BellaBot or BellaBot Pro: what changes?']"
          @pick="pick"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Centered in the whole window, 20 px above the middle (as in Figma 01 · Ask). */
.home { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; pointer-events: none; }
.block { width: min(var(--column-width), calc(100% - 32px)); display: flex; flex-direction: column; align-items: center; transform: translateY(-20px); pointer-events: auto; }
.title { text-align: center; }
.subtitle { text-align: center; color: var(--color-text-secondary); margin-top: 12px; }
.composer { margin-top: 40px; }
.starts { width: 100%; display: flex; gap: 16px; margin-top: 24px; }
/* low windows: the home block starts under the top bar and scrolls instead of being cut */
@media (max-height: 760px) {
  .home { top: var(--top-bar-height); align-items: flex-start; overflow-y: auto; pointer-events: auto; padding: 8px 0 24px; }
  .block { transform: none; }
}
/* narrow windows: the two starting cards stack */
@media (max-width: 760px) { .starts { flex-direction: column; } }
</style>

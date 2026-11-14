<script setup>
import { ref, nextTick } from 'vue'
import Icon from './Icon.vue'
import { useVoice } from '../api/useVoice.js'
const emit = defineEmits(['submit'])
const text = ref('')
const area = ref(null)
const grow = async () => { await nextTick(); const el = area.value; if (!el) return; el.style.height = '30px'; el.style.height = el.scrollHeight + 'px' }
// The text is not cleared on submit: the home view leaves and the typed question morphs into the title.
const submit = () => { if (!text.value.trim()) return; emit('submit', text.value) }
const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }
// An example question is first written into the field, so it visibly travels from here to the title.
const fill = async (q) => { text.value = q; await grow() }
defineExpose({ fill })
// microphone (backend voice.js): the recognised question is sent like a typed one
const voice = useVoice(async (said) => { await fill(said); submit() })
</script>

<template>
  <!-- view-transition-name: the composer becomes the prompt bar at the bottom, its text becomes the question title -->
  <form class="composer squircle" style="view-transition-name: input-bar" @submit.prevent="submit">
    <div class="input" style="view-transition-name: question">
      <textarea
        ref="area" v-model="text" rows="1" class="t-body-large"
        :placeholder="voice.placeholder('Ask anything about PUDU robots and accessories')"
        aria-label="Your question" @input="grow" @keydown="onKey"
      />
    </div>
    <div class="toolbar">
      <button
        v-if="voice.available.value" type="button" class="icon-btn icon-btn--ghost" :aria-pressed="voice.state.value === 'listening'"
        :aria-label="voice.state.value === 'listening' ? 'Stop listening' : 'Ask with your voice'" @click="voice.toggle()"
      ><Icon name="mic" /></button>
      <button
        type="submit" class="icon-btn" :class="text.trim() ? 'icon-btn--inverse' : 'icon-btn--surface send-empty'"
        aria-label="Send"
      ><Icon name="arrow_upward" /></button>
    </div>
  </form>
</template>

<style scoped>
.composer {
  width: 100%;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-2xl);
  padding: 20px 8px 8px;
  box-shadow: var(--elevation-1-raised);   /* the place to type sits above the page */
  display: flex; flex-direction: column; gap: 12px;
}
.input { padding: 0 16px 20px; }
textarea { width: 100%; height: 30px; min-height: 30px; max-height: 240px; display: block; }
.toolbar { display: flex; justify-content: flex-end; gap: 4px; }
.send-empty { color: var(--color-text-tertiary); }
</style>

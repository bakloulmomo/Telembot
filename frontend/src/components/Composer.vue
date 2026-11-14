<script setup>
import { ref, nextTick } from 'vue'
import Icon from './Icon.vue'
import { useVoice } from '../api/useVoice.js'
const emit = defineEmits(['submit'])
const text = ref('')
const area = ref(null)
const grow = async () => { await nextTick(); const el = area.value; if (!el) return; el.style.height = '30px'; el.style.height = el.scrollHeight + 'px' }
const submit = () => { if (!text.value.trim()) return; emit('submit', text.value); text.value = ''; grow() }
const onKey = (e) => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit() }
  if (e.key === 'Escape') voice.cancel()
}
// the recognised question is sent at once, like a typed one
const voice = useVoice((said) => { text.value = said; submit() })
</script>

<template>
  <form class="composer squircle" @submit.prevent="submit">
    <div class="input">
      <textarea
        ref="area" v-model="text" rows="1" class="t-body-large"
        :placeholder="voice.placeholder('Ask anything about PUDU robots and accessories')"
        aria-label="Your question" @input="grow" @keydown="onKey"
      />
    </div>
    <div class="toolbar">
      <button
        v-if="voice.available.value" type="button" class="icon-btn icon-btn--ghost"
        :class="{ 'is-listening': voice.state.value !== 'idle' }" :aria-pressed="voice.state.value === 'listening'"
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
  display: flex; flex-direction: column; gap: 12px;
}
.input { padding: 0 16px 20px; }
textarea { width: 100%; height: 30px; min-height: 30px; max-height: 240px; display: block; }
.toolbar { display: flex; justify-content: flex-end; gap: 4px; }
.send-empty { color: var(--color-text-tertiary); }
.is-listening { color: var(--color-text-primary); }
</style>

<script setup>
// States from Figma: idle (Empty / Typed), busy (answer loading: Send becomes Stop), reply (inside the clarification card).
import { ref } from 'vue'
import Icon from './Icon.vue'
import { useVoice } from '../api/useVoice.js'
const props = defineProps({
  mode: { type: String, default: 'idle' },
  placeholder: { type: String, default: 'Ask a follow-up' },
})
const emit = defineEmits(['submit', 'stop'])
const text = ref('')
const submit = () => {
  if (props.mode === 'busy') return emit('stop')
  if (!text.value.trim()) return
  emit('submit', text.value)
  text.value = ''
}
// the recognised question is sent at once, like a typed one
const voice = useVoice((said) => { if (props.mode === 'busy') return; text.value = said; submit() })
</script>

<template>
  <form class="prompt-bar squircle" :class="`is-${mode}`" @submit.prevent="submit">
    <Icon v-if="mode === 'reply'" name="subdirectory_arrow_right" class="reply-icon" />
    <input
      v-model="text" class="t-body-large" :placeholder="voice.placeholder(placeholder)" :aria-label="placeholder"
      @keydown.esc="voice.cancel()"
    />
    <button
      v-if="voice.available.value" type="button" class="icon-btn icon-btn--ghost"
      :class="{ 'is-listening': voice.state.value !== 'idle' }" :aria-pressed="voice.state.value === 'listening'"
      :aria-label="voice.state.value === 'listening' ? 'Stop listening' : 'Ask with your voice'"
      :disabled="mode === 'busy'" @click="voice.toggle()"
    ><Icon name="mic" /></button>
    <button v-if="mode === 'busy'" type="submit" class="icon-btn icon-btn--stop" aria-label="Stop the answer">
      <span class="stop-square"></span>
    </button>
    <button
      v-else type="submit" class="icon-btn"
      :class="text.trim() ? 'icon-btn--inverse' : mode === 'reply' ? 'icon-btn--elevated' : 'icon-btn--surface send-empty'"
      aria-label="Send"
    ><Icon name="arrow_upward" /></button>
  </form>
</template>

<style scoped>
.prompt-bar {
  width: 100%; height: 60px;
  display: flex; align-items: center; gap: 4px;
  padding: 8px 8px 8px 24px;
  border-radius: var(--radius-2xl);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-subtle);
}
.prompt-bar.is-reply { background: var(--color-bg-surface); border-color: transparent; padding-left: 20px; gap: 8px; }
.reply-icon { color: var(--color-text-secondary); }
input { flex: 1; min-width: 0; height: 30px; }
.send-empty { color: var(--color-text-tertiary); }
.stop-square { width: 14px; height: 14px; border-radius: 3px; background: var(--color-text-highlight); display: block; }
.is-listening { color: var(--color-text-primary); }
button:disabled { cursor: default; }
</style>

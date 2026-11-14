// The microphone: backend/app/static/voice.js (transcription on the server with OPENAI_API_KEY,
// otherwise the browser's own speech recognition). The design has no listening state yet:
// only the placeholder changes ("Listening…") and the mic button is marked as pressed.
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { createVoiceInput } from '@voice'

export function useVoice(onText) {
  const state = ref('idle')          // idle | listening | transcribing
  const available = ref(true)        // the button is in the design: it stays until we know it cannot work
  const message = ref('')
  let voice = null
  let timer

  onMounted(async () => {
    voice = await createVoiceInput({
      onText,
      onState: (s) => { state.value = s; if (s === 'listening') message.value = '' },
      onError: (m) => { message.value = m; clearTimeout(timer); timer = setTimeout(() => (message.value = ''), 4000) },
    })
    available.value = voice.mode !== null
  })
  onBeforeUnmount(() => { voice?.cancel(); clearTimeout(timer) })

  const placeholder = (fallback) =>
    message.value || (state.value === 'listening' ? 'Listening…' : state.value === 'transcribing' ? 'Transcribing…' : fallback)

  return { state, available, placeholder, toggle: () => voice?.toggle(), cancel: () => voice?.cancel() }
}

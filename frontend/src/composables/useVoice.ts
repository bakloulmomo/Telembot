// Il microfono: usa voice.js del backend (trascrizione sul server o riconoscimento del browser).

import { onBeforeUnmount, onMounted, ref } from "vue";
import { createVoiceInput, type VoiceInput, type VoiceState } from "@voice";

export function useVoice(onText: (text: string) => void) {
  const state = ref<VoiceState>("idle");
  const available = ref(false);
  const error = ref("");
  let voice: VoiceInput | null = null;
  let errorTimer: number | undefined;

  onMounted(async () => {
    voice = await createVoiceInput({
      onText,
      onState: s => { state.value = s; if (s === "listening") error.value = ""; },
      onError: message => {
        error.value = message;
        window.clearTimeout(errorTimer);
        errorTimer = window.setTimeout(() => (error.value = ""), 4000);
      },
    });
    available.value = voice.mode !== null;
  });

  onBeforeUnmount(() => { voice?.cancel(); window.clearTimeout(errorTimer); });

  return {
    state,
    available,
    error,
    toggle: () => voice?.toggle(),
    cancel: () => voice?.cancel(),
  };
}

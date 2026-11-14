<script setup lang="ts">
// Campo della domanda. home: grande al centro (01 · Ask); dock: in basso ("Ask a follow-up");
// reply: dentro la scheda di chiarimento (02 · Clarify).
import { computed, nextTick, onMounted, ref } from "vue";
import Icon from "./Icon.vue";
import { useVoice } from "@/composables/useVoice";

const props = defineProps<{
  variant: "home" | "dock" | "reply";
  placeholder: string;
  busy?: boolean;
  autofocus?: boolean;
}>();
const emit = defineEmits<{ send: [text: string]; stop: [] }>();

const text = ref("");
const field = ref<HTMLTextAreaElement | null>(null);
const root = ref<HTMLFormElement | null>(null);
defineExpose({ root, focus: () => field.value?.focus() });

const voice = useVoice(said => { text.value = said; void nextTick(submit); });

const hasText = computed(() => text.value.trim().length > 0);
const shownPlaceholder = computed(() =>
  voice.error.value || (voice.state.value === "listening" ? "Listening…"
    : voice.state.value === "transcribing" ? "Transcribing…" : props.placeholder));

function grow() {
  const el = field.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
}

function submit() {
  if (props.busy) return;
  const t = text.value.trim();
  if (!t) return;
  emit("send", t);
  text.value = "";
  void nextTick(grow);
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); }
  if (e.key === "Escape" && voice.state.value === "listening") voice.cancel();
}

function onButton() {
  if (props.busy) emit("stop");
  else submit();
}

onMounted(() => { if (props.autofocus) field.value?.focus(); grow(); });
</script>

<template>
  <form ref="root" class="composer" :class="[variant, { 'has-text': hasText, listening: voice.state.value === 'listening' }]" @submit.prevent="submit">
    <Icon v-if="variant === 'reply'" name="reply" :size="20" class="reply-icon" />
    <label class="sr-only" :for="`q-${variant}`">{{ placeholder }}</label>
    <textarea
      :id="`q-${variant}`" ref="field" v-model="text" rows="1" :placeholder="shownPlaceholder"
      enterkeyhint="send" autocomplete="off" @input="grow" @keydown="onKey"
    />
    <div class="actions">
      <button
        v-if="voice.available.value" type="button" class="mic" :class="voice.state.value"
        :aria-label="voice.state.value === 'listening' ? 'Stop listening' : 'Ask with your voice'"
        :aria-pressed="voice.state.value === 'listening'" :disabled="busy || voice.state.value === 'transcribing'"
        @click="voice.toggle()"
      >
        <span v-if="voice.state.value === 'transcribing'" class="mini-spinner" />
        <Icon v-else name="mic" :size="18" />
      </button>
      <button
        :type="busy ? 'button' : 'submit'" class="send" :class="{ ready: hasText || busy, busy }"
        :aria-label="busy ? 'Stop' : 'Send'" :disabled="!busy && !hasText" @click.prevent="onButton"
      >
        <Transition name="swap" mode="out-in">
          <Icon v-if="busy" key="stop" name="stop" :size="20" />
          <Icon v-else key="send" name="arrow-up" :size="18" />
        </Transition>
      </button>
    </div>
  </form>
</template>

<style scoped>
.composer {
  position: relative; display: flex; width: 100%;
  background: var(--surface); border: 1px solid var(--line);
  transition: border-color .2s ease, box-shadow .25s ease;
}
.composer:focus-within { border-color: #dcdcda; box-shadow: 0 2px 14px rgb(0 0 0 / .04); }

textarea {
  flex: 1; min-width: 0; resize: none; border: 0; outline: none; background: transparent;
  font-size: 19px; line-height: 28px; color: var(--text); padding: 0; max-height: 220px;
}
textarea::placeholder { color: #8d8d8d; transition: color .2s ease; }
.listening textarea::placeholder { color: var(--danger); }

/* 01 · Ask */
.home { flex-direction: column; min-height: 134px; border-radius: 28px; padding: 21px 8px 8px 24px; }
.home textarea { flex: none; width: 100%; min-height: 56px; padding-right: 16px; }
.home .actions { align-self: flex-end; }

/* domanda di seguito, in basso */
.dock { align-items: center; min-height: 60px; border-radius: var(--radius-composer); padding: 7px 7px 7px 24px; }
.dock textarea { padding: 9px 0; }

/* risposta al chiarimento */
.reply { align-items: center; min-height: 60px; border-radius: var(--radius-composer); padding: 7px 7px 7px 20px;
  background: var(--well); border-color: transparent; }
.reply:focus-within { box-shadow: none; border-color: #dededc; }
.reply textarea { padding: 9px 0; }
.reply-icon { color: #8d8d8d; margin-right: 10px; flex: none; }

.actions { display: flex; align-items: center; gap: 6px; flex: none; }

.mic, .send {
  display: inline-flex; align-items: center; justify-content: center; border: 0; border-radius: 50%;
  transition: background-color .2s ease, color .2s ease, transform .15s var(--ease), opacity .2s ease;
}
.mic { width: 40px; height: 40px; background: transparent; color: #4a4a4a; }
.mic:hover:not(:disabled) { background: var(--well); }
.mic:disabled { opacity: .45; cursor: default; }
.mic.listening { background: var(--danger); color: #fff; animation: pulse-ring 1.2s ease-out infinite; }

.send { width: 44px; height: 44px; background: var(--well); color: #8d8d8d; }
.reply .send { background: var(--surface); }
.send.ready { background: var(--ink); color: #fff; }
.send:disabled { cursor: default; }
.send:not(:disabled):active { transform: scale(.92); }

.mini-spinner { width: 16px; height: 16px; border-radius: 50%; border: 2px solid #d4d4d2; border-top-color: var(--text);
  animation: spin .7s linear infinite; }

.swap-enter-active, .swap-leave-active { transition: opacity .15s ease, transform .15s var(--ease); }
.swap-enter-from, .swap-leave-to { opacity: 0; transform: scale(.6); }

@media (max-width: 640px) {
  textarea { font-size: 17px; }
  .home { min-height: 120px; padding-left: 18px; }
  .dock { padding-left: 18px; }
}
</style>

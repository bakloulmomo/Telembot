<script setup lang="ts">
// Icone del design, a tratto. size in px; il colore segue il testo (currentColor).
defineProps<{
  name: "mic" | "arrow-up" | "stop" | "check" | "pause" | "close" | "arrow-right" | "external"
    | "sparkle" | "warn" | "reply" | "stop-circle" | "retry";
  size?: number;
}>();
</script>

<template>
  <svg
    :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"
  >
    <template v-if="name === 'mic'">
      <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" />
    </template>
    <path v-else-if="name === 'arrow-up'" d="M12 19V5M6 11l6-6 6 6" />
    <rect v-else-if="name === 'stop'" x="7" y="7" width="10" height="10" rx="2" fill="currentColor" stroke="none" />
    <path v-else-if="name === 'check'" d="M5 12.5l4.5 4.5L19 7.5" />
    <template v-else-if="name === 'pause'">
      <circle cx="12" cy="12" r="9" /><path d="M10 9v6M14 9v6" />
    </template>
    <path v-else-if="name === 'close'" d="M6 6l12 12M18 6L6 18" />
    <path v-else-if="name === 'arrow-right'" d="M5 12h14M13 6l6 6-6 6" />
    <template v-else-if="name === 'external'">
      <path d="M14 4h6v6M20 4l-9 9" /><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" />
    </template>
    <template v-else-if="name === 'sparkle'">
      <path d="M12 4l1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6z" /><path d="M19 15l.7 1.8 1.8.7-1.8.7L19 20l-.7-1.8-1.8-.7 1.8-.7z" />
    </template>
    <template v-else-if="name === 'warn'">
      <path d="M12 4L2.5 20h19z" /><path d="M12 10v4.5M12 17.2v.3" />
    </template>
    <path v-else-if="name === 'reply'" d="M5 5v6a3 3 0 0 0 3 3h11M15 10l4 4-4 4" />
    <template v-else-if="name === 'stop-circle'">
      <circle cx="12" cy="12" r="9" /><rect x="9" y="9" width="6" height="6" rx="1" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'retry'">
      <path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4.5h4.5" />
    </template>
  </svg>
</template>

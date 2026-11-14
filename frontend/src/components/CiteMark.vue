<script setup lang="ts">
// Il numero della fonte in un cerchietto: ① nel testo, ❷ quando è aperta o sotto il mouse.
defineProps<{ n: number; active?: boolean; size?: "sm" | "md" | "lg"; as?: "button" | "span" }>();
defineEmits<{ open: [n: number]; hover: [n: number | null] }>();
</script>

<template>
  <button
    v-if="(as ?? 'button') === 'button'"
    type="button" class="cite" :class="[size ?? 'sm', { active }]"
    :aria-label="`Open source ${n}`" :aria-pressed="active"
    @click.stop="$emit('open', n)" @mouseenter="$emit('hover', n)" @mouseleave="$emit('hover', null)"
    @focus="$emit('hover', n)" @blur="$emit('hover', null)"
  >{{ n }}</button>
  <span v-else class="cite" :class="[size ?? 'sm', { active }]" aria-hidden="true">{{ n }}</span>
</template>

<style scoped>
.cite {
  display: inline-flex; align-items: center; justify-content: center; flex: none;
  padding: 0; border: 1.2px solid currentColor; border-radius: 50%;
  background: transparent; color: #9a9a9a; font-weight: 500; line-height: 1;
  font-variant-numeric: tabular-nums;
  transition: color .15s ease, background-color .15s ease, border-color .15s ease, transform .2s var(--ease);
  animation: pop .35s var(--ease) both;
}
.sm { width: 14px; height: 14px; font-size: 8.5px; margin: 0 1px 0 4px; vertical-align: 0.2em; }
.md { width: 18px; height: 18px; font-size: 10.5px; }
.lg { width: 22px; height: 22px; font-size: 12.5px; border-width: 1.6px; color: var(--text); }
button.cite:hover { color: var(--text); transform: scale(1.12); }
.cite.active { background: var(--text); border-color: var(--text); color: #fff; }
</style>

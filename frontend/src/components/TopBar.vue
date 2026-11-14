<script setup>
import Icon from './Icon.vue'
defineProps({ showBrand: { type: Boolean, default: true }, counts: { type: String, default: '' } })
defineEmits(['open-chats'])
</script>

<template>
  <header class="top-bar">
    <div v-if="showBrand" class="left">
      <button class="icon-btn icon-btn--ghost menu" aria-label="Open chats" @click="$emit('open-chats')">
        <Icon name="left_panel_open" :size="20" />
      </button>
      <img class="mark" src="/brand/telmekom-mark.png" width="24" height="24" alt="Telmekom" />
      <span class="t-headline">Telembot</span>
    </div>
    <!-- drawer open: the counts move to the left edge of the page area (screen 00) -->
    <span class="t-callout-regular counts">{{ counts }}</span>
  </header>
</template>

<style scoped>
.top-bar {
  height: var(--top-bar-height);
  padding: 0 var(--top-bar-padding-x) 0 28px;
  display: flex; align-items: center; justify-content: space-between;
  flex: none;
}
.left { display: flex; align-items: center; gap: 8px; }
.menu { color: var(--color-text-primary); }
.mark { display: block; flex: none; }
.counts { color: var(--color-text-secondary); }
@media (max-width: 640px) {
  .top-bar { padding: 0 16px 0 12px; }
  .counts { display: none; }      /* no room next to the brand on a phone */
}
</style>

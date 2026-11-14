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
      <span class="t-headline">Telembot</span>
    </div>
    <span v-else></span>
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
.counts { color: var(--color-text-secondary); }
</style>

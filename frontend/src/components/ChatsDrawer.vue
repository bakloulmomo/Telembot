<script setup>
import Icon from './Icon.vue'
// groups: { 'Today': [{ id, q, pinned }], 'Past chats': [...] }. Pinned chats are listed first in their group.
defineProps({ groups: { type: Object, required: true }, activeId: { type: String, default: null } })
defineEmits(['close', 'new-chat', 'open', 'pin'])
const sorted = (items) => [...items].sort((a, b) => Number(b.pinned) - Number(a.pinned))
</script>

<template>
  <aside class="drawer" aria-label="Chats">
    <div class="header">
      <button class="icon-btn icon-btn--ghost close" aria-label="Close chats" @click="$emit('close')">
        <Icon name="left_panel_close" :size="20" />
      </button>
      <span class="t-headline">Telembot</span>
    </div>
    <div class="new-wrap">
      <button class="new squircle" @click="$emit('new-chat')">
        <Icon name="add" :size="20" />
        <span class="t-callout-strong">New chat</span>
      </button>
    </div>
    <section v-for="(items, label) in groups" :key="label" class="group">
      <p class="t-overline label">{{ label }}</p>
      <div
        v-for="c in sorted(items)" :key="c.id"
        class="row squircle" :class="{ active: c.id === activeId, pinned: c.pinned }"
      >
        <button class="open t-callout-regular" @click="$emit('open', c.id)">{{ c.q }}</button>
        <button class="pin" :aria-label="c.pinned ? 'Unpin chat' : 'Pin chat'" :aria-pressed="c.pinned" @click="$emit('pin', c.id)">
          <Icon name="push_pin" :filled="c.pinned" />
        </button>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.drawer {
  width: 300px; flex: none; height: 100%;
  background: var(--color-bg-elevated);
  border-right: 1px solid var(--color-border-subtle);
  display: flex; flex-direction: column; overflow-y: auto;
}
.header { height: 84px; flex: none; display: flex; align-items: center; gap: 8px; padding: 0 16px 0 28px; }
.close { color: var(--color-text-primary); }
.new-wrap { padding: 4px 16px 8px; }
.new {
  width: 100%; height: 44px; border-radius: var(--radius-xl);
  background: var(--color-bg-surface); color: var(--color-text-primary);
  display: flex; align-items: center; gap: 10px; padding: 0 16px 0 12px;
}
.group { display: flex; flex-direction: column; gap: 2px; padding: 20px 16px 0; }
.label { color: var(--color-text-tertiary); padding: 0 0 8px 12px; }
.row { display: flex; align-items: center; gap: 8px; padding: 0 12px; border-radius: var(--radius-md); }
.open {
  flex: 1; min-width: 0; text-align: left; padding: 10px 0; color: var(--color-text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pin { width: 20px; height: 20px; display: none; color: var(--color-text-primary); }
.row:hover, .row.active { background: var(--color-bg-surface); }
.row:hover .pin { display: block; }
.row.pinned .pin { display: block; color: var(--color-text-tertiary); }
.row.pinned:hover .pin { color: var(--color-text-primary); }
</style>

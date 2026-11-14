<script setup>
// Not part of the design: a small panel to jump to each Figma screen while testing. Hide it with ?clean=1.
import { ref } from 'vue'
defineProps({ live: Boolean })
defineEmits(['jump'])
const open = ref(true)
const screens = ['00', '01', '01.5', '02', '03a', '03c', '04a', '04b']
</script>

<template>
  <div class="proto" :class="{ closed: !open }">
    <button class="toggle" @click="open = !open">{{ open ? 'Hide' : 'Prototype' }}</button>
    <template v-if="open">
      <span class="mode">{{ live ? 'Live backend' : 'Mock data' }}</span>
      <button v-for="s in screens" :key="s" class="screen" @click="$emit('jump', s)">{{ s }}</button>
    </template>
  </div>
</template>

<style scoped>
.proto {
  position: fixed; left: 16px; bottom: 16px; z-index: 50;
  display: flex; align-items: center; gap: 4px; padding: 6px;
  background: var(--neutral-950); color: var(--neutral-0); border-radius: 12px;
  font: 500 12px/16px var(--font-text);
}
.proto button { color: inherit; padding: 6px 8px; border-radius: 8px; }
.proto button:hover { background: rgba(255, 255, 255, 0.12); }
.mode { padding: 0 8px; opacity: 0.6; }
</style>

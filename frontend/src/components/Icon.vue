<script setup>
// Material Symbols Rounded, outlined by default. Sizes from the design: 24, 20, 16 (17 for inline source numbers).
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 20 },
  filled: { type: Boolean, default: false },
})
</script>

<template>
  <span
    class="icon"
    :class="[`icon-${size === 17 ? 20 : size}`, { 'icon-filled': filled }]"
    :style="size === 17 ? { fontSize: '17px', width: '17px', height: '17px' } : null"
    aria-hidden="true"
  >{{ name }}</span>
</template>

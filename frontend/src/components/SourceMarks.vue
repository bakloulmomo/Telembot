<script setup>
// Inline source numbers: U+202F narrow no-break space, then Material "counter_N" at 17 px.
defineProps({ ns: { type: Array, default: () => [] }, size: { type: Number, default: 17 } })
</script>

<template><span v-if="ns.length" class="marks">&#8239;<span
  v-for="n in ns" :key="n" class="icon mark" :style="{ fontSize: size + 'px' }" aria-hidden="true"
>counter_{{ n }}</span><span class="sr-only">(source {{ ns.join(', ') }})</span></span></template>

<style scoped>
.marks { white-space: nowrap; }
.mark {
  display: inline-block; vertical-align: -2px; line-height: 1;
  color: var(--color-text-tertiary);
  font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 20;
}
.mark + .mark { margin-left: 2px; }
</style>

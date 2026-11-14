<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import SourceMarks from './SourceMarks.vue'
const props = defineProps({ comparison: { type: Object, required: true } })
const cols = computed(() => props.comparison.products)
const grid = computed(() => ({ gridTemplateColumns: `164px repeat(${cols.value.length}, minmax(0, 1fr))` }))
const isRec = (id) => props.comparison.recommended?.includes(id)
const at = (row, col) => ({ gridRow: row, gridColumn: col })   // every cell is placed explicitly
const lastRow = computed(() => props.comparison.rows.length + 1)
</script>

<template>
  <div class="table" role="table" :style="grid">
    <!-- recommended columns: surface background, inset 4 px each side so neighbours never touch -->
    <template v-for="(p, ci) in cols" :key="'hl-' + p.id">
      <span v-if="isRec(p.id)" class="highlight squircle" :style="{ gridColumn: ci + 2, gridRow: `1 / ${lastRow + 1}` }"></span>
    </template>

    <span class="cell head" role="columnheader" :style="at(1, 1)"></span>
    <span v-for="(p, ci) in cols" :key="'h-' + p.id" class="cell head" role="columnheader" :style="at(1, ci + 2)">
      <span class="t-body-strong">{{ p.name }}</span><SourceMarks :ns="p.n ? [p.n] : []" :size="16" />
    </span>

    <template v-for="(row, ri) in comparison.rows" :key="row.label">
      <span class="cell label t-callout-regular" :class="{ last: ri + 2 === lastRow }" role="rowheader" :style="at(ri + 2, 1)">{{ row.label }}</span>
      <span
        v-for="(p, ci) in cols" :key="row.label + p.id" class="cell" :class="{ last: ri + 2 === lastRow }"
        role="cell" :style="at(ri + 2, ci + 2)"
      >
        <template v-if="row.kind === 'fit'">
          <span v-if="row.values[p.id]" class="fit yes"><Icon name="check_circle" /><span class="t-callout-medium">Yes</span></span>
          <span v-else class="fit no"><Icon name="cancel" /><span class="t-callout-regular">No</span></span>
        </template>
        <span v-else class="t-callout-regular value">{{ row.values[p.id] ?? '–' }}</span>
      </span>
    </template>
  </div>
</template>

<style scoped>
.table { display: grid; position: relative; width: 100%; }
.highlight { margin: 0 4px; border-radius: var(--radius-md); background: var(--color-bg-surface); z-index: 0; }
.cell {
  position: relative; z-index: 1;
  min-height: 44px; padding: 12px 8px 12px 12px;
  display: flex; align-items: center; gap: 6px;
  border-bottom: 1px solid var(--color-border-subtle);
}
.cell.last { border-bottom: 0; }
.cell.head { min-height: 64px; }
.label { color: var(--color-text-secondary); }
.value { color: var(--color-text-primary); }
.fit { display: inline-flex; align-items: center; gap: 6px; }
.fit.yes { color: var(--color-text-success); }
.fit.yes .icon { color: var(--color-icon-success); }
.fit.no { color: var(--color-text-secondary); }
.fit.no .icon { color: var(--color-text-tertiary); }
</style>

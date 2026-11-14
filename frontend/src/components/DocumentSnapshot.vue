<script setup>
// A "photograph" of the manual page: white paper on a surface, running header, verbatim text,
// cited lines in lime, cut at the bottom with a fade. Never show AI figure descriptions here.
import { ref, onMounted, onUpdated, nextTick } from 'vue'
const props = defineProps({
  document: String,
  page: [Number, String],
  heading: String,
  subheading: String,
  kind: { type: String, default: 'bullets' },  // bullets | table | figure | mixed (real sections: { type, text, cells })
  lines: { type: Array, default: () => [] },
  cited: { type: Array, default: () => [] },   // indexes of cited lines
  image: Object,                                // { url, width, height }
  height: { type: Number, default: 344 },       // minimum height
  cut: { type: Boolean, default: true },
})
// The cut never hides a cited line: the snapshot grows until the last cited line is 8 px above the 56 px fade.
const shot = ref(null)
const h = ref(props.height)
const fit = async () => {
  await nextTick()
  const el = shot.value
  if (!el || props.kind === 'figure') return
  const cited = el.querySelectorAll('.cited')
  const last = cited[cited.length - 1]
  const need = last ? last.offsetTop + last.offsetHeight + 8 + 56 : 0
  const full = el.querySelector('.paper').offsetTop + el.querySelector('.paper').offsetHeight
  h.value = Math.min(full, Math.max(props.height, need))
}
onMounted(fit)
onUpdated(fit)
</script>

<template>
  <div ref="shot" class="shot squircle" :style="kind === 'figure' ? null : { height: h + 'px' }">
    <div class="paper" :class="{ 'is-figure': kind === 'figure' }">
      <div class="running t-caption"><span>{{ document }}</span><span>{{ page }}</span></div>
      <p v-if="heading" class="t-callout-strong heading">{{ heading }}</p>
      <p v-if="subheading" class="t-footnote-strong subheading">{{ subheading }}</p>
      <template v-if="kind === 'bullets'">
        <p v-for="(l, i) in lines" :key="i" class="line t-callout-regular" :class="{ cited: cited.includes(i) }">
          <span>•</span><span>{{ l }}</span>
        </p>
      </template>
      <template v-else-if="kind === 'table'">
        <p v-for="(r, i) in lines" :key="i" class="line row t-callout-regular" :class="{ cited: cited.includes(i) }">
          <span>{{ r[0] }}</span><span>{{ r[1] }}</span>
        </p>
      </template>
      <template v-else-if="kind === 'mixed'">
        <template v-for="(l, i) in lines" :key="i">
          <p v-if="l.type === 'sub'" class="t-footnote-strong subheading">{{ l.text }}</p>
          <p v-else-if="l.type === 'row'" class="line row t-callout-regular" :class="{ cited: cited.includes(i) }">
            <span>{{ l.cells[0] }}</span><span>{{ l.cells[1] }}</span>
          </p>
          <p v-else class="line t-callout-regular" :class="{ cited: cited.includes(i) }">
            <span v-if="l.type === 'li'">•</span><span>{{ l.text }}</span>
          </p>
        </template>
      </template>
      <div v-else class="figure">
        <img :src="image.url" :width="image.width" :height="image.height" alt="Figure from the manual" />
      </div>
    </div>
    <span v-if="cut && kind !== 'figure'" class="fade" aria-hidden="true"></span>
  </div>
</template>

<style scoped>
.shot {
  position: relative; overflow: hidden;
  background: var(--color-bg-surface); border-radius: var(--radius-lg);
  padding: 20px 20px 0;
}
.paper {
  background: var(--neutral-0);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-xs);
  box-shadow: var(--shadow-small);
  padding: 16px 24px 40px;
  display: flex; flex-direction: column; gap: 10px;
}
.paper.is-figure { padding-bottom: 16px; margin-bottom: 20px; }
.running {
  display: flex; justify-content: space-between;
  color: var(--color-text-tertiary);
  padding-bottom: 8px; border-bottom: 1px solid var(--color-border-subtle); margin-bottom: 2px;
}
.heading { color: var(--color-text-primary); }
.subheading { color: var(--color-text-secondary); }
.line { display: flex; gap: 8px; padding: 3px 6px; border-radius: var(--radius-xs); color: var(--color-text-secondary); }
.line.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.line.cited { background: var(--color-bg-accent-subtle); color: var(--color-text-primary); }
.figure { display: flex; justify-content: center; }
.figure img { display: block; max-width: 100%; height: auto; }
.fade {
  position: absolute; left: 0; right: 0; bottom: 0; height: 56px;
  background: linear-gradient(to bottom, rgba(246, 246, 243, 0), var(--color-bg-surface));
}
</style>

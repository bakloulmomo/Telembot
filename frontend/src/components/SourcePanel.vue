<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import DocumentSnapshot from './DocumentSnapshot.vue'
import { guessCitedLines } from '../api/parse.js'
// Two states: a source of a claim (citation), or "Not in the manuals" for an unverified part (gap).
const props = defineProps({
  citation: { type: Object, default: null },
  gap: { type: Object, default: null },
  cited: { type: Array, default: null },     // cited snapshot lines for the selected claim
  claimText: { type: String, default: '' },
})
defineEmits(['close'])
const LANGS = { en: 'English', de: 'German', it: 'Italian' }
const c = computed(() => props.citation || {})
const g = computed(() => props.gap)
const tree = computed(() => ['PUDU manuals', c.value.family || 'Robots', c.value.product_name, LANGS[c.value.lang] || c.value.lang].filter(Boolean))
const pageText = computed(() => [c.value.page, c.value.pdf_page && `PDF page ${c.value.pdf_page}${c.value.page_side ? `, ${c.value.page_side} column` : ''}`].filter(Boolean).join(' · '))
const citedLines = computed(() => props.cited ?? guessCitedLines(c.value.snapshot?.lines, props.claimText))
const doc = computed(() => c.value)
</script>

<template>
  <aside class="panel" :class="{ 'is-gap': g }" :aria-label="g ? 'Not in the manuals' : 'Source'">
    <header class="header">
      <Transition name="pop" mode="out-in"><span v-if="!g" :key="c.n" class="icon icon-24 num" aria-hidden="true">counter_{{ c.n }}</span></Transition>
      <h2 class="t-headline title">{{ g ? 'Not in the manuals' : 'Source' }}</h2>
      <button class="icon-btn icon-btn--surface" aria-label="Close" @click="$emit('close')"><Icon name="close" /></button>
    </header>

    <!-- switching to another claim: the content crossfades (160 ms) and the highlighter is drawn again -->
    <Transition name="xfade" mode="out-in">
    <div v-if="g" :key="'gap|' + claimText" class="body">
      <section class="doc">
        <p class="tree-row"><Icon name="search" :size="16" /><span class="t-footnote-regular tree">Searched all 22 manuals · English, German, Italian</span></p>
        <p class="t-title-small">{{ g.topic || g.text }}</p>
        <dl class="rows">
          <div v-if="g.asked"><dt class="t-callout-regular">Asked</dt><dd class="t-callout-regular">{{ g.asked }}</dd></div>
          <div v-if="g.found"><dt class="t-callout-regular">Found</dt><dd class="t-callout-regular found">{{ g.found }}</dd></div>
        </dl>
      </section>
      <section v-if="g.note" class="ai squircle">
        <p class="ai-label"><Icon name="auto_awesome" :size="16" /><span class="t-footnote-strong">Why the answer says it could not verify it · written by AI</span></p>
        <p class="t-callout-regular">{{ g.note }}</p>
      </section>
    </div>

    <div v-else :key="`${c.n}|${claimText}`" class="body">
      <section class="doc">
        <p class="tree-row"><Icon name="folder" :size="16" /><span class="t-footnote-regular tree">{{ tree.join('  ›  ') }}</span></p>
        <p class="t-title-small">{{ c.document }}</p>
        <dl class="rows">
          <div v-if="c.section_path"><dt class="t-callout-regular">Section</dt><dd class="t-callout-regular">{{ c.section_path }}</dd></div>
          <div v-if="pageText"><dt class="t-callout-regular">Page</dt><dd class="t-callout-regular">{{ pageText }}</dd></div>
          <div v-if="c.line"><dt class="t-callout-regular">Line</dt><dd class="t-callout-regular">{{ c.line }}</dd></div>
        </dl>
      </section>

      <hr />

      <section class="block">
        <p class="t-overline label">In the manual</p>
        <DocumentSnapshot
          :document="c.document" :page="c.page"
          :heading="c.snapshot?.heading" :subheading="c.snapshot?.subheading"
          :kind="c.snapshot?.kind" :lines="c.snapshot?.lines" :cited="citedLines"
          :height="c.snapshot?.height" :cut="c.snapshot?.cut"
        />
      </section>

      <template v-for="f in c.figures || []" :key="f.url">
        <hr />
        <section class="block">
          <p class="t-overline label">Figure in the manual</p>
          <DocumentSnapshot kind="figure" :document="c.document" :page="f.page" :image="f" />
          <p v-if="f.caption" class="t-footnote-regular caption">{{ f.caption }}</p>
        </section>
      </template>

      <section v-if="c.note" class="ai squircle">
        <p class="ai-label"><Icon name="auto_awesome" :size="16" /><span class="t-footnote-strong">How the answer uses it · written by AI</span></p>
        <p class="t-callout-regular">{{ c.note }}</p>
      </section>
    </div>
    </Transition>

    <!-- no footer in the Not in the manuals state: there is no page to open -->
    <footer v-if="!g" class="footer">
      <a class="open" :href="doc.pdf_url || '#'" target="_blank" rel="noopener">
        <Icon name="open_in_new" />
        <span class="t-body-strong">Open manual at page {{ c.page }}</span>
      </a>
      <p v-if="doc.pdf_file" class="t-footnote-regular caption center">
        {{ doc.pdf_file }}<template v-if="doc.pdf_page"> · PDF page {{ doc.pdf_page }}, passage highlighted</template>
      </p>
    </footer>
  </aside>
</template>

<style scoped>
.panel {
  width: var(--panel-width); flex: none; height: 100%;   /* the slot is the window height: only .body scrolls */
  background: var(--color-bg-elevated);
  border-left: 1px solid var(--color-border-subtle);
  box-shadow: var(--elevation-3-sheet-left);
  display: flex; flex-direction: column;
}
.header { height: 84px; flex: none; display: flex; align-items: center; gap: 12px; padding: 0 20px 0 32px; }
.num { color: var(--color-text-primary); }
.title { flex: 1; }
.body { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 4px 32px 32px; display: flex; flex-direction: column; gap: 24px; }
hr { border: 0; height: 1px; background: var(--color-border-subtle); margin: 0; }
.doc { display: flex; flex-direction: column; gap: 12px; }
.tree-row { display: flex; align-items: center; gap: 6px; color: var(--color-text-tertiary); }
.tree { color: var(--color-text-tertiary); white-space: pre; }
.rows { margin: 0; padding-top: 4px; display: flex; flex-direction: column; gap: 6px; }
.rows div { display: flex; gap: 12px; }
.rows dt { width: 72px; flex: none; color: var(--color-text-tertiary); }
.rows dd { margin: 0; color: var(--color-text-primary); }
.block { display: flex; flex-direction: column; gap: 12px; }
.label { color: var(--color-text-tertiary); }
.caption { color: var(--color-text-secondary); }
.caption.center { text-align: center; color: var(--color-text-tertiary); }
.ai {
  border: 1px solid var(--color-border-subtle); border-radius: var(--radius-lg);
  padding: 18px 20px 20px; display: flex; flex-direction: column; gap: 10px;
}
.ai-label { display: flex; align-items: center; gap: 6px; color: var(--color-text-secondary); }
.footer {
  flex: none; padding: 20px 32px 32px; display: flex; flex-direction: column; gap: 10px;
  border-top: 1px solid var(--color-border-subtle); background: var(--color-bg-elevated);
}
.open {
  height: 56px; border-radius: var(--radius-full); padding: 0 24px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  background: var(--color-bg-inverse); color: var(--color-text-inverse); text-decoration: none;
}
/* Not in the manuals: the amber of the unverified sentence comes back in the panel,
   so it is clearly different from a found source. Header band amber-subtle, title and "Found" in amber text. */
.is-gap .header { background: var(--color-bg-warning-subtle); }
.is-gap .title, .is-gap .found { color: var(--color-text-warning); }
/* close button on the amber band: near-white circle, amber X (the grey one disappeared on amber) */
.is-gap .header .icon-btn { background: var(--color-bg-elevated); color: var(--color-text-warning); }
.is-gap .body { padding-top: 24px; }

/* narrow windows: the panel lies over the page and is never wider than the window */
@media (max-width: 1099px) { .panel { width: min(var(--panel-width), 100vw); } }
@media (max-width: 640px) {
  .header { padding: 0 16px 0 20px; }
  .body { padding: 4px 20px 24px; }
  .footer { padding: 16px 20px 20px; }
}
</style>

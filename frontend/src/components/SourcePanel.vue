<script setup>
import { computed, ref, watch } from 'vue'
import Icon from './Icon.vue'
import DocumentSnapshot from './DocumentSnapshot.vue'
import { guessCitedLines } from '../api/parse.js'
import { loadSource, panelCitation } from '../api/backend.js'
const props = defineProps({
  citation: { type: Object, required: true },
  cited: { type: Array, default: null },     // cited snapshot lines for the selected claim
  claimText: { type: String, default: '' },
})
defineEmits(['close'])
const LANGS = { en: 'English', de: 'German', it: 'Italian' }

// Live backend: the citation points to its section (/api/sources/…); load it and show the manual's own text.
// Mock data already carries document, snapshot and figures.
const section = ref(null)
const live = computed(() => !props.citation.snapshot && !!props.citation.source_url)
watch(() => props.citation.source_url, async (url) => {
  section.value = null
  if (!url || props.citation.snapshot) return
  try { section.value = await loadSource(url) } catch { section.value = null }
}, { immediate: true })
const c = computed(() => (props.citation.snapshot ? props.citation : panelCitation(props.citation, section.value)))
const tree = computed(() => ['PUDU manuals', c.value.family || 'Robots', c.value.product_name, LANGS[c.value.lang] || c.value.lang].filter(Boolean))
const pageText = computed(() => [c.value.page, c.value.pdf_page && `PDF page ${c.value.pdf_page}${c.value.page_side ? `, ${c.value.page_side} column` : ''}`].filter(Boolean).join(' · '))
const citedLines = computed(() => props.cited ?? guessCitedLines(c.value.snapshot?.lines, props.claimText))
</script>

<template>
  <aside class="panel" aria-label="Source">
    <header class="header">
      <span class="icon icon-24 num" aria-hidden="true">counter_{{ c.n }}</span>
      <h2 class="t-headline title">Source</h2>
      <button class="icon-btn icon-btn--surface" aria-label="Close source" @click="$emit('close')"><Icon name="close" /></button>
    </header>

    <div class="body">
      <section class="doc">
        <p class="t-footnote-regular tree">{{ tree.join('  ›  ') }}</p>
        <p class="t-title-small">{{ c.document }}</p>
        <dl class="rows">
          <div v-if="c.section_path"><dt class="t-callout-regular">Section</dt><dd class="t-callout-regular">{{ c.section_path }}</dd></div>
          <div v-if="pageText"><dt class="t-callout-regular">Page</dt><dd class="t-callout-regular">{{ pageText }}</dd></div>
          <div v-if="c.line"><dt class="t-callout-regular">Line</dt><dd class="t-callout-regular">{{ c.line }}</dd></div>
        </dl>
      </section>

      <hr />

      <section v-if="c.snapshot" class="block">
        <p class="t-overline label">In the manual</p>
        <DocumentSnapshot
          :key="`${c.n}-${c.source_url}-${!!section}`" :document="c.document" :page="c.page"
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

    <footer class="footer">
      <a class="open" :href="c.pdf_url || '#'" target="_blank" rel="noopener">
        <Icon name="open_in_new" />
        <span class="t-body-strong">Open manual at page {{ c.page ?? c.pdf_page }}</span>
      </a>
      <!-- the real PDF opens on the right page; highlighting the passage inside it is not built yet -->
      <p v-if="c.pdf_file" class="t-footnote-regular caption center">
        {{ c.pdf_file }}<template v-if="c.pdf_page"> · PDF page {{ c.pdf_page }}<template v-if="!live">, passage highlighted</template><template v-else-if="c.page_side">, {{ c.page_side }} column</template></template>
      </p>
    </footer>
  </aside>
</template>

<style scoped>
.panel {
  width: var(--panel-width); flex: none; height: 100%;
  background: var(--color-bg-elevated);
  border-left: 1px solid var(--color-border-subtle);
  display: flex; flex-direction: column;
}
.header { height: 84px; flex: none; display: flex; align-items: center; gap: 12px; padding: 0 20px 0 32px; }
.num { color: var(--color-text-primary); }
.title { flex: 1; }
.body { flex: 1; overflow-y: auto; padding: 4px 32px 32px; display: flex; flex-direction: column; gap: 24px; }
hr { border: 0; height: 1px; background: var(--color-border-subtle); margin: 0; }
.doc { display: flex; flex-direction: column; gap: 12px; }
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
</style>

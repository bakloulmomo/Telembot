<script setup lang="ts">
// 04a · Source panel e 04b · Source panel · figure: da dove viene una parte della risposta.
import { computed, ref, watch } from "vue";
import CiteMark from "./CiteMark.vue";
import Icon from "./Icon.vue";
import { sentencesFor } from "@/lib/answer";
import { getSource, type Citation, type SourceSection } from "@/lib/api";
import { describePassage, findPassage, passageWindow, splitSection } from "@/lib/passage";

const props = defineProps<{ citation: Citation; answer: string }>();
const emit = defineEmits<{ close: [] }>();

const source = ref<SourceSection | null>(null);
const loading = ref(false);
const failed = ref(false);
const showAllLabels = ref(false);

watch(() => props.citation.source_url, async url => {
  source.value = null;
  failed.value = false;
  showAllLabels.value = false;
  if (!url) return;
  loading.value = true;
  try { source.value = await getSource(url); }
  catch { failed.value = true; }
  finally { loading.value = false; }
}, { immediate: true });

const LANG_NAMES: Record<string, string> = { en: "English", de: "German", it: "Italian" };

const blocks = computed(() => (source.value ? splitSection(source.value.markdown) : []));
const picked = computed(() => findPassage(blocks.value, sentencesFor(props.answer, props.citation.n), props.citation.text));
const pickedSet = computed(() => new Set(picked.value));
const view = computed(() => {
  const [a, b] = passageWindow(blocks.value, picked.value);
  return { blocks: blocks.value.slice(a, b).map((blk, k) => ({ blk, i: a + k })), cut: b < blocks.value.length };
});

const manualTitle = computed(() => source.value?.manual_title
  || (props.citation.product_name ? `${props.citation.product_name} User Manual` : props.citation.label));

const crumbs = computed(() => {
  const s = source.value;
  const out = ["PUDU manuals"];
  if (s) out.push(s.category === "accessory" ? "Accessories" : "Robots");
  if (props.citation.product_name) out.push(props.citation.product_name);
  const lang = s?.lang ?? props.citation.lang;
  if (lang) out.push(LANG_NAMES[lang] ?? lang);
  return out;
});

const sectionLine = computed(() => {
  const s = source.value;
  if (!s) return props.citation.section_title;
  const own = s.number ? `${s.number} ${s.title}` : s.title;
  return s.parent_title ? `${s.parent_number}. ${s.parent_title} › ${own}` : (s.number && !s.number.includes(".") ? `${s.number}. ${s.title}` : own);
});

const pageLine = computed(() => {
  const s = source.value;
  const page = s?.page ?? props.citation.page;
  if (!page && !s?.pdf_page) return null;
  const pdf = s?.pdf_page ? `PDF page ${s.pdf_page}${s.pdf_side ? `, ${s.pdf_side} column` : ""}` : "";
  return [page, pdf].filter(Boolean).join(" · ");
});

const passageLine = computed(() => describePassage(blocks.value, picked.value));

const pdfUrl = computed(() => source.value?.pdf_url ?? props.citation.pdf_url);
const pdfCaption = computed(() => {
  const s = source.value;
  if (!s?.pdf_file) return null;
  return `${s.pdf_file}${s.pdf_page ? ` · PDF page ${s.pdf_page}${s.pdf_side ? `, ${s.pdf_side} column` : ""}` : ""}`;
});

function figurePage(url: string): string | null {
  const m = /-p0*(\d+)([LR])?-fig/i.exec(url);
  return m ? `PDF page ${m[1]}${m[2] ? `, ${m[2] === "L" ? "left" : "right"}` : ""}` : null;
}
function shortCaption(text: string | null): string | null {
  if (!text) return null;
  const first = text.split(/(?<=[.!?])\s/)[0];
  return first.length > 140 ? `${first.slice(0, 137)}…` : first;
}
</script>

<template>
  <aside class="panel" aria-label="Source" @keydown.esc="emit('close')">
    <header class="top">
      <h2><CiteMark :n="citation.n" size="lg" as="span" /> Source</h2>
      <button type="button" class="icon-btn" aria-label="Close source" @click="emit('close')"><Icon name="close" :size="18" /></button>
    </header>

    <div class="scroll">
      <Transition name="swap" mode="out-in">
        <div :key="`${citation.n}-${citation.source_url}`" class="content">
          <nav class="crumbs" aria-label="Location">
            <template v-for="(c, i) in crumbs" :key="c"><span v-if="i" class="sep">›</span>{{ c }}</template>
          </nav>
          <h3 class="title">{{ manualTitle }}</h3>

          <dl class="meta">
            <template v-if="sectionLine"><dt>Section</dt><dd>{{ sectionLine }}</dd></template>
            <template v-if="pageLine"><dt>Page</dt><dd>{{ pageLine }}</dd></template>
            <template v-if="passageLine"><dt>Line</dt><dd>{{ passageLine }}</dd></template>
          </dl>

          <hr />

          <section>
            <h4 class="eyebrow">In the manual</h4>
            <div class="well">
              <article class="page" :class="{ cut: view.cut }">
                <header class="page-head"><span>{{ manualTitle }}</span><span>{{ source?.page ?? citation.page ?? "" }}</span></header>
                <template v-if="loading">
                  <div class="sk w80" /><div class="sk" /><div class="sk w60" />
                </template>
                <template v-else-if="source">
                  <h5 class="sec-title">{{ source.number ? `${source.number} ${source.title}` : source.title }}</h5>
                  <div
                    v-for="{ blk, i } in view.blocks" :key="i" class="blk" :class="[blk.kind, { hl: pickedSet.has(i), dim: picked.length && !pickedSet.has(i) && blk.kind !== 'label' && blk.kind !== 'heading' }]"
                  >
                    <!-- eslint-disable-next-line vue/no-v-html -- markdown-it con html: false -->
                    <span v-html="blk.html" />
                  </div>
                </template>
                <p v-else class="blk p">{{ citation.text || (failed ? "The section could not be loaded." : "") }}</p>
              </article>
            </div>
          </section>

          <section v-for="f in citation.figures" :key="f.url" class="figure-block">
            <h4 class="eyebrow">Figure in the manual</h4>
            <div class="well">
              <article class="page">
                <header class="page-head"><span>{{ manualTitle }}</span><span>{{ figurePage(f.url) ?? "" }}</span></header>
                <a :href="f.url" target="_blank" rel="noopener" class="figure-link">
                  <img :src="f.url" :alt="shortCaption(f.caption) ?? 'Figure from the manual'" loading="lazy" />
                </a>
              </article>
            </div>
            <p class="fig-cap">{{ [shortCaption(f.caption), source && (source.number ? `${source.number} ${source.title}` : source.title), figurePage(f.url)].filter(Boolean).join(" · ") }}</p>
            <ul v-if="f.labels.length" class="legend" :class="{ open: showAllLabels }">
              <li v-for="(l, k) in (showAllLabels ? f.labels : f.labels.slice(0, 8))" :key="k"><b>{{ l.n ?? "•" }}</b>{{ l.text }}</li>
            </ul>
            <button v-if="f.labels.length > 8" type="button" class="more" @click="showAllLabels = !showAllLabels">
              {{ showAllLabels ? "Show fewer labels" : `Show all ${f.labels.length} labels` }}
            </button>
          </section>

          <section v-if="citation.note" class="note">
            <h4><Icon name="sparkle" :size="15" /> How the answer uses it · written by AI</h4>
            <p>{{ citation.note }}</p>
          </section>
        </div>
      </Transition>
    </div>

    <footer v-if="pdfUrl" class="foot">
      <a class="open" :href="pdfUrl" target="_blank" rel="noopener">
        <Icon name="external" :size="18" /> Open manual at page {{ source?.page ?? citation.page ?? source?.pdf_page ?? "" }}
      </a>
      <p v-if="pdfCaption" class="foot-cap">{{ pdfCaption }}</p>
    </footer>
  </aside>
</template>

<style scoped>
.panel {
  width: var(--panel); height: 100%; display: flex; flex-direction: column;
  background: var(--surface); border-left: 1px solid var(--line);
}
.top { display: flex; align-items: center; justify-content: space-between; padding: 0 20px 0 32px; height: 84px; flex: none; }
h2 { display: flex; align-items: center; gap: 12px; margin: 0; font-size: 21px; font-weight: 500; letter-spacing: -0.01em; }

.scroll { flex: 1; overflow-y: auto; padding: 0 32px 32px; overscroll-behavior: contain; }
.content { padding-top: 4px; }

.crumbs { font-size: 13.5px; color: var(--muted); display: flex; flex-wrap: wrap; align-items: center; }
.sep { margin: 0 7px; color: #a3a3a3; }
.title { margin: 14px 0 18px; font-size: 24px; line-height: 30px; font-weight: 600; letter-spacing: -0.015em; }

.meta { display: grid; grid-template-columns: 84px 1fr; row-gap: 6px; margin: 0; font-size: 15px; line-height: 20px; }
dt { color: #8d8d8d; }
dd { margin: 0; color: var(--text); }

hr { border: 0; border-top: 1px solid var(--line); margin: 24px 0 28px; }

.eyebrow { margin: 0 0 14px; font-size: 12.5px; font-weight: 500; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }

.well { background: var(--well); border-radius: 18px; padding: 20px 20px 0; overflow: hidden; }
.page {
  position: relative; background: #fff; border-radius: 4px 4px 0 0; padding: 16px 24px 20px;
  box-shadow: 0 0 0 1px rgb(0 0 0 / .04), 0 4px 14px rgb(0 0 0 / .04);
  max-height: 300px; overflow: hidden;
}
.page.cut::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 64px;
  background: linear-gradient(to bottom, rgb(255 255 255 / 0), #fff);
}
.page-head {
  display: flex; justify-content: space-between; gap: 12px; font-size: 12.5px; color: var(--muted);
  padding-bottom: 10px; margin-bottom: 22px; border-bottom: 1px solid #ececea;
}
.sec-title { margin: 0 0 12px; font-size: 15px; font-weight: 600; }

.blk { font-size: 15px; line-height: 20px; color: #333; margin: 0 0 12px; transition: color .3s ease, background-color .3s ease; }
.blk.label, .blk.heading { font-weight: 600; color: var(--text-2); font-size: 13.5px; margin-bottom: 8px; }
.blk.li { position: relative; padding: 6px 8px 6px 20px; margin: 0 -8px 8px; border-radius: 3px; }
.blk.li::before { content: "•"; position: absolute; left: 7px; top: 6px; color: inherit; }
.blk.p { padding: 6px 8px; margin: 0 -8px 8px; border-radius: 3px; }
.blk.dim { color: #8a8a8a; }
.blk.hl { background: var(--mark); color: var(--text); animation: mark-in .6s var(--ease) both; }
@keyframes mark-in { from { background-color: transparent; } }
.blk.table :deep(table) { width: 100%; border-collapse: collapse; font-size: 13.5px; line-height: 18px; }
.blk.table :deep(td), .blk.table :deep(th) { border-bottom: 1px solid #eee; padding: 5px 6px; text-align: left; vertical-align: top; }
.blk.table :deep(th) { font-weight: 600; }
.blk.table.hl { padding: 4px; margin: 0 -4px 8px; }

.sk { height: 12px; border-radius: 6px; margin: 10px 0 14px; width: 100%;
  background: linear-gradient(90deg, #f1f1ef 25%, #e8e8e6 37%, #f1f1ef 63%); background-size: 400% 100%; animation: shimmer 1.4s ease infinite; }
.sk.w80 { width: 80%; } .sk.w60 { width: 60%; }

.figure-block { margin-top: 32px; }
.figure-block .page { max-height: none; padding-bottom: 24px; }
.figure-link { display: block; }
.figure-link img { margin: 0 auto; max-height: 320px; object-fit: contain; }
.fig-cap { margin: 12px 0 0; font-size: 13.5px; line-height: 19px; color: var(--muted); }
.legend { list-style: none; margin: 12px 0 0; padding: 0; columns: 2; column-gap: 20px; font-size: 13.5px; line-height: 19px; color: var(--text-2); }
.legend li { break-inside: avoid; padding: 2px 0; }
.legend b { display: inline-block; min-width: 24px; color: var(--text); font-weight: 600; font-variant-numeric: tabular-nums; }
.more { margin-top: 8px; padding: 4px 0; border: 0; background: none; font-size: 13.5px; font-weight: 500; color: var(--blue); }

.note { margin-top: 24px; border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px 20px; }
.note h4 { display: flex; align-items: center; gap: 6px; margin: 0 0 10px; font-size: 13.5px; font-weight: 500; color: var(--text-2); }
.note p { margin: 0; font-size: 15.5px; line-height: 21px; }

.foot { flex: none; border-top: 1px solid var(--line); padding: 20px 32px 18px; }
.open {
  display: flex; align-items: center; justify-content: center; gap: 10px; height: 56px; border-radius: 28px;
  background: var(--ink); color: #fff; font-size: 17px; font-weight: 600; text-decoration: none;
  transition: transform .15s var(--ease), background-color .2s ease;
}
.open:hover { background: #2a2a2a; }
.open:active { transform: scale(.985); }
.foot-cap { margin: 12px 0 0; text-align: center; font-size: 13px; color: var(--muted); overflow-wrap: anywhere; }

.swap-enter-active, .swap-leave-active { transition: opacity .18s ease, transform .22s var(--ease); }
.swap-enter-from { opacity: 0; transform: translateY(6px); }
.swap-leave-to { opacity: 0; }

@media (max-width: 1100px) { .panel { width: min(var(--panel), 100vw); } }
@media (max-width: 640px) {
  .top { padding: 12px 12px 0 16px; height: 64px; }
  .scroll { padding: 0 16px 24px; }
  .foot { padding: 16px; }
}
</style>

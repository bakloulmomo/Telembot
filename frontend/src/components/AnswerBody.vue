<script setup lang="ts">
// 03a · Answer · prose e 03b · Answer · numbered. Sotto il mouse (o con la fonte aperta)
// la frase citata si evidenzia; le parti non verificate sono in arancione.
import { computed, ref } from "vue";
import CiteMark from "./CiteMark.vue";
import Icon from "./Icon.vue";
import { parseAnswer } from "@/lib/answer";
import type { Citation } from "@/lib/api";

const props = defineProps<{
  answer: string;
  citations: Citation[];
  gaps: string[];
  streaming: boolean;
  openN: number | null;
}>();
const emit = defineEmits<{ open: [n: number] }>();

const hover = ref<number | null>(null);
const parsed = computed(() => parseAnswer(props.answer));
const lit = computed(() => hover.value ?? props.openN);
const known = computed(() => new Set(props.citations.map(c => c.n)));

const figures = computed(() =>
  props.citations.flatMap(c => c.figures.map(f => ({ ...f, n: c.n, label: c.label }))));

function open(n: number) { if (known.value.has(n)) emit("open", n); }
</script>

<template>
  <div class="answer" :class="parsed.layout">
    <!-- 03b: un punto per riga, con la sua fonte a sinistra -->
    <template v-if="parsed.layout === 'numbered'">
      <div
        v-for="(block, bi) in parsed.blocks" :key="bi" class="row"
        :class="{ lit: lit !== null && block.cites.includes(lit), clickable: block.cites.length, para: block.kind === 'p' }"
        @mouseenter="hover = block.cites[0] ?? null" @mouseleave="hover = null"
        @click="block.cites.length && open(block.cites[0])"
      >
        <span class="lead">
          <CiteMark v-if="block.cites.length" :n="block.cites[0]" size="md" as="span" :active="lit === block.cites[0]" />
          <span v-else class="dot" />
        </span>
        <span class="row-text">
          <template v-for="(seg, si) in block.segments" :key="si">
            <template v-for="(part, pi) in seg.parts" :key="pi"><b v-if="part.bold">{{ part.text }}</b><template v-else>{{ part.text }}</template></template>
          </template>
          <span v-if="streaming && bi === parsed.blocks.length - 1" class="caret" />
        </span>
      </div>
      <div v-for="gap in gaps" :key="gap" class="row gap-row">
        <span class="lead"><Icon name="warn" :size="17" /></span>
        <span class="row-text">{{ gap }}</span>
      </div>
    </template>

    <!-- 03a: testo continuo con i numeri delle fonti -->
    <template v-else>
      <component
        :is="block.kind === 'li' ? 'li' : 'p'" v-for="(block, bi) in parsed.blocks" :key="bi"
        :class="{ item: block.kind === 'li' }"
      >
        <template v-for="(seg, si) in block.segments" :key="si">{{ seg.lead }}<span class="claim" :class="{ lit: lit !== null && seg.cites.includes(lit) }"><template v-for="(part, pi) in seg.parts" :key="pi"><b v-if="part.bold">{{ part.text }}</b><template v-else>{{ part.text }}</template></template></span><CiteMark
            v-for="n in seg.cites" :key="n" :n="n" :active="lit === n" @open="open" @hover="hover = $event"
          />
        </template>
        <span v-if="streaming && bi === parsed.blocks.length - 1" class="caret" />
      </component>
      <p v-for="gap in gaps" :key="gap" class="gap"><span class="gap-text">{{ gap }}<Icon name="warn" :size="16" class="gap-icon" /></span></p>
    </template>

    <span v-if="streaming && !parsed.blocks.length" class="caret" />

    <!-- figure scelte dal motore: si aprono nel pannello della fonte -->
    <div v-if="figures.length && !streaming" class="figures">
      <button v-for="f in figures" :key="f.url" type="button" class="figure" @click="open(f.n)">
        <img :src="f.url" :alt="f.caption ?? `Figure from source ${f.n}`" loading="lazy" />
        <span class="figure-cap"><CiteMark :n="f.n" as="span" />{{ f.label }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.answer { font-size: 19px; line-height: 30px; color: var(--text); overflow-wrap: anywhere; }

p, li.item { margin: 0 0 20px; }
li.item { list-style: disc; margin-left: 22px; padding-left: 2px; }
p:last-child { margin-bottom: 0; }

.claim {
  border-radius: 6px; padding: 2px 0; -webkit-box-decoration-break: clone; box-decoration-break: clone;
  text-decoration: underline 1px transparent; text-underline-offset: 4px;
  transition: background-color .18s ease, text-decoration-color .18s ease, box-shadow .18s ease;
}
.claim.lit { background: var(--well); box-shadow: -4px 0 0 var(--well), 4px 0 0 var(--well); text-decoration-color: var(--text); }

.gap { margin: -20px 0 0; }
.gap-text {
  color: var(--warn); background: var(--warn-bg); border-radius: 6px; padding: 3px 6px; margin: 0 -6px;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; animation: fade-up .4s var(--ease) both;
}
.gap-icon { display: inline; vertical-align: -2px; margin-left: 4px; }

/* 03b */
.numbered { display: flex; flex-direction: column; gap: 4px; margin: 0 -12px; }
.row {
  display: grid; grid-template-columns: 20px 1fr; column-gap: 12px; padding: 12px; border-radius: 10px;
  transition: background-color .18s ease; animation: fade-up .35s var(--ease) both;
}
.row.clickable { cursor: pointer; }
.row.lit { background: var(--well); }
.row.para { grid-template-columns: 1fr; }
.row.para .lead { display: none; }
.lead { height: 30px; display: flex; align-items: center; justify-content: center; color: #9a9a9a; }
.row.lit .lead { color: var(--text); }
.dot { width: 5px; height: 5px; border-radius: 50%; background: #b5b5b3; }
.gap-row { color: var(--warn); background: var(--warn-bg); }
.gap-row .lead { color: var(--warn); }

.caret {
  display: inline-block; width: 11px; height: 11px; margin-left: 6px; border-radius: 50%;
  background: var(--text); vertical-align: 0.05em; animation: caret 1s ease-in-out infinite;
}

.figures { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 28px; }
.numbered .figures { margin: 24px 12px 0; }
.figure {
  display: flex; flex-direction: column; gap: 8px; width: 200px; padding: 10px; text-align: left;
  border: 1px solid var(--line); border-radius: 14px; background: var(--surface);
  transition: border-color .2s ease, transform .2s var(--ease), box-shadow .2s ease; animation: fade-up .4s var(--ease) both;
}
.figure:hover { border-color: #d6d6d4; transform: translateY(-2px); box-shadow: 0 6px 18px rgb(0 0 0 / .05); }
.figure img { width: 100%; height: 120px; object-fit: contain; background: #fff; border-radius: 6px; }
.figure-cap { display: flex; align-items: center; gap: 6px; font-size: 13px; line-height: 17px; color: var(--muted); }
.figure-cap :deep(.cite) { margin: 0; }

@media (max-width: 640px) { .answer { font-size: 17px; line-height: 27px; } }
</style>

<script setup>
import Icon from './Icon.vue'
defineProps({ icon: String, title: String, description: String, questions: Array })
defineEmits(['pick'])
</script>

<template>
  <section class="card squircle">
    <div class="header">
      <div class="title-row">
        <Icon :name="icon" />
        <h2 class="t-body-strong">{{ title }}</h2>
      </div>
      <p class="t-callout-regular description">{{ description }}</p>
    </div>
    <button v-for="q in questions" :key="q" class="example" @click="$emit('pick', q)">
      <span class="t-callout-regular">{{ q }}</span>
      <Icon name="arrow_forward" class="arrow" />
    </button>
  </section>
</template>

<style scoped>
.card {
  flex: 1 1 0; min-width: 0;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding-bottom: 4px;
  display: flex; flex-direction: column;
}
.header { padding: 20px 20px 18px; display: flex; flex-direction: column; gap: 6px; }
.title-row { display: flex; align-items: center; gap: 10px; color: var(--color-text-primary); }
.description { color: var(--color-text-secondary); }
.example {
  display: flex; align-items: center; gap: 12px; padding: 12px 20px;
  border-top: 1px solid var(--color-border-subtle);
  text-align: left; color: var(--color-text-primary);
}
.example span:first-child { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.arrow { color: var(--color-text-tertiary); }
</style>

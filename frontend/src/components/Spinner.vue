<!-- Spinner 20: track #EFEFEB (surface-strong), arc ink. The rotation is the only motion in this build. -->
<template>
  <svg class="spinner" width="20" height="20" viewBox="0 0 20 20" role="img" aria-label="Loading">
    <circle cx="10" cy="10" r="8.25" fill="none" stroke="var(--color-bg-surface-strong)" stroke-width="2.5" />
    <circle cx="10" cy="10" r="8.25" fill="none" stroke="var(--color-text-primary)" stroke-width="2.5"
            stroke-linecap="round" stroke-dasharray="13 52" transform="rotate(-90 10 10)" />
  </svg>
</template>

<style scoped>
.spinner { display: block; animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }
</style>

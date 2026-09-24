<template>
  <div class="app-card">
    <slot />
  </div>
</template>

<style scoped>
.app-card {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}
</style>

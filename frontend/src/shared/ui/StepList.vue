<script setup lang="ts">
export interface Step {
  title: string
  text?: string
}

// Нумерованные шаги: на узком экране — колонкой, на широком — в ряд карточек.
defineProps<{ steps: Step[] }>()
</script>

<template>
  <ol class="step-list">
    <li v-for="(step, index) in steps" :key="index" class="step-list__item">
      <span class="step-list__number">{{ index + 1 }}</span>
      <div class="step-list__body">
        <p class="step-list__title">{{ step.title }}</p>
        <p v-if="step.text" class="step-list__text">{{ step.text }}</p>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.step-list {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.step-list__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.step-list__number {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: color-mix(in srgb, var(--color-primary) 10%, var(--color-surface));
  border-radius: var(--radius-badge);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-label);
  font-variant-numeric: tabular-nums;
}

.step-list__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.step-list__title {
  font-weight: var(--font-weight-label);
}

.step-list__text {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

@media (min-width: 768px) {
  .step-list {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .step-list__item {
    flex-direction: column;
  }
}
</style>

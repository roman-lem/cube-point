<script setup lang="ts">
import { FAQ } from '@/shared/config'
import { AppIcon } from '@/shared/ui'

// Accordion on native <details>: keyboard and screen readers work out of the box,
// several answers can be open at once.
</script>

<template>
  <div class="faq">
    <details v-for="item in FAQ" :key="item.question" class="faq__item">
      <summary class="faq__question">
        {{ item.question }}
        <AppIcon name="expand-more" :size="20" class="faq__chevron" />
      </summary>
      <p class="faq__answer">
        <template v-for="(piece, index) in item.answer" :key="index">
          <template v-if="typeof piece === 'string'">{{ piece }}</template>
          <RouterLink v-else :to="piece.to">{{ piece.text }}</RouterLink>
        </template>
      </p>
    </details>
  </div>
</template>

<style scoped>
.faq {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.faq__item {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.faq__question {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  font-weight: var(--font-weight-label);
  list-style: none;
  cursor: pointer;
}

/* Safari shows its own marker otherwise. */
.faq__question::-webkit-details-marker {
  display: none;
}

.faq__question:focus-visible {
  border-radius: var(--radius-card);
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.faq__chevron {
  flex-shrink: 0;
  color: var(--color-text-secondary);
  transition: transform 0.2s;
}

.faq__item[open] .faq__chevron {
  transform: rotate(180deg);
}

.faq__answer {
  padding: 0 var(--space-4) var(--space-4);
  color: var(--color-text-secondary);
}

.faq__answer a {
  color: var(--color-primary);
}
</style>

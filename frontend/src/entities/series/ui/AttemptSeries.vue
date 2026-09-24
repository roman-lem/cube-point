<script setup lang="ts">
import { computed } from 'vue'
import {
  ATTEMPTS_COUNT,
  calcSeries,
  formatAttempt,
  type Attempt,
  type ResultType,
  type SeriesFormat,
} from '@/shared/lib'

// Попытки серии в ряд, отброшенные в ao5 — в скобках, несобранные — пустые.
const { attempts, format, resultType = 'time' } = defineProps<{
  attempts: (Attempt | null)[]
  format: SeriesFormat
  resultType?: ResultType
}>()

const cells = computed(() => {
  const count = ATTEMPTS_COUNT[format]
  const filled = Array.from({ length: count }, (_, i) => attempts[i] ?? null)
  // calcSeries ждёт несобранные попытки только в конце списка.
  const entered = [...filled]
  while (entered.length > 0 && entered[entered.length - 1] === null) {
    entered.pop()
  }
  const { counting } = calcSeries(entered, format, resultType)
  return filled.map((attempt, i) => {
    const text = attempt ? formatAttempt(attempt, resultType) : ''
    return {
      text: attempt && !counting[i] ? `(${text})` : text,
      isDnf: attempt?.penalty === 'dnf' || attempt?.penalty === 'dns',
    }
  })
})
</script>

<template>
  <ol class="attempt-series">
    <li
      v-for="(cell, i) in cells"
      :key="i"
      :class="['attempt-series__cell', { 'attempt-series__cell--dnf': cell.isDnf }]"
      :aria-label="`Попытка ${i + 1}: ${cell.text || 'не собрана'}`"
    >
      {{ cell.text }}
    </li>
  </ol>
</template>

<style scoped>
.attempt-series {
  display: grid;
  grid-auto-columns: minmax(0, 1fr);
  grid-auto-flow: column;
  gap: var(--space-1);
  padding: 0;
  list-style: none;
}

.attempt-series__cell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 2px;
  background: var(--color-background);
  border-radius: var(--radius-badge);
  font-family: var(--font-mono);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.attempt-series__cell--dnf {
  color: var(--color-dnf);
}
</style>

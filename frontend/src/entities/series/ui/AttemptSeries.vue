<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  ATTEMPTS_COUNT,
  calcSeries,
  formatAttempt,
  type ResultType,
  type SeriesFormat,
} from '@/shared/lib'
import type { SeriesAttempt } from '../model/types'

// Series attempts in a row: ones dropped in ao5 in parentheses, ones not yet done empty.
// An attempt corrected by an organizer has a corner mark; tapping it shows the
// original value under the row. FMC solutions, if the server sent them, are listed below.
const { attempts, format, resultType = 'time' } = defineProps<{
  attempts: (SeriesAttempt | null)[]
  format: SeriesFormat
  resultType?: ResultType
}>()

const cells = computed(() => {
  const count = ATTEMPTS_COUNT[format]
  const filled = Array.from({ length: count }, (_, i) => attempts[i] ?? null)
  // calcSeries expects attempts not yet done only at the end of the list.
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
      original: attempt?.edited && attempt.original
        ? formatAttempt(attempt.original, resultType)
        : null,
    }
  })
})

const solutions = computed(() =>
  attempts.flatMap((attempt, i) => (attempt?.solution ? [{ number: i + 1, text: attempt.solution }] : [])),
)

/** Index (zero-based) of the attempt whose original value is shown. */
const shown = ref<number | null>(null)
const shownOriginal = computed(() => (shown.value === null ? null : cells.value[shown.value]?.original))

function toggle(i: number) {
  shown.value = shown.value === i ? null : i
}
</script>

<template>
  <div class="attempt-series">
    <ol class="attempt-series__row">
      <li
        v-for="(cell, i) in cells"
        :key="i"
        :class="['attempt-series__cell', { 'attempt-series__cell--dnf': cell.isDnf }]"
        :aria-label="cell.original ? undefined : `Попытка ${i + 1}: ${cell.text || 'не собрана'}`"
      >
        <button
          v-if="cell.original"
          type="button"
          class="attempt-series__edited"
          :aria-expanded="shown === i"
          :aria-label="`Попытка ${i + 1}: ${cell.text}, исправлена организатором`"
          @click="toggle(i)"
        >
          {{ cell.text }}
        </button>
        <template v-else>{{ cell.text }}</template>
      </li>
    </ol>
    <p v-if="shownOriginal" class="attempt-series__original">
      Попытку {{ shown! + 1 }} исправил организатор, исходно:
      <span class="attempt-series__original-value">{{ shownOriginal }}</span>
    </p>
    <dl v-if="solutions.length" class="attempt-series__solutions">
      <div v-for="solution in solutions" :key="solution.number" class="attempt-series__solution">
        <dt>{{ ATTEMPTS_COUNT[format] > 1 ? `Решение ${solution.number}` : 'Решение' }}</dt>
        <dd class="attempt-series__solution-moves">{{ solution.text }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.attempt-series {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.attempt-series__row {
  display: grid;
  grid-auto-columns: minmax(0, 1fr);
  grid-auto-flow: column;
  gap: var(--space-1);
  padding: 0;
  list-style: none;
}

.attempt-series__cell {
  position: relative;
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

.attempt-series__edited {
  width: 100%;
  min-height: 32px;
  padding: 0;
  background: none;
  border: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

/* Mark of a corrected attempt: a corner, like a note in a spreadsheet. */
.attempt-series__edited::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  border-top: 8px solid var(--color-primary);
  border-left: 8px solid transparent;
  border-top-right-radius: var(--radius-badge);
}

.attempt-series__original {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.attempt-series__solutions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-label);
}

.attempt-series__solution dt {
  color: var(--color-text-secondary);
}

.attempt-series__solution-moves {
  margin: 0;
  font-family: var(--font-mono);
  word-spacing: 0.2em;
}

.attempt-series__original-value {
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
</style>

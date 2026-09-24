<script setup lang="ts">
import { computed, ref } from 'vue'
import { formatAttempt } from '@/shared/lib'
import type { TrainingPenalty, TrainingSolve } from '../model/session'
import TrainingSolveActions from './TrainingSolveActions.vue'

// Сборки сессии, новые сверху, с правкой штрафа и удалением.
// Сначала показываются последние VISIBLE, остальные — по кнопке.
const VISIBLE = 12

const { solves } = defineProps<{ solves: TrainingSolve[] }>()

const emit = defineEmits<{
  penalty: [at: number, penalty: TrainingPenalty]
  remove: [solve: TrainingSolve, number: number]
}>()

const showAll = ref(false)

const rows = computed(() => {
  const numbered = solves.map((solve, i) => ({ solve, number: i + 1 })).reverse()
  return showAll.value ? numbered : numbered.slice(0, VISIBLE)
})
</script>

<template>
  <div class="solve-list">
    <ol class="solve-list__items">
      <li v-for="{ solve, number } in rows" :key="solve.at" class="solve-list__row">
        <span class="solve-list__number">#{{ number }}</span>
        <span :class="['solve-list__time', { 'solve-list__time--dnf': solve.penalty === 'dnf' }]">
          {{ formatAttempt(solve, 'time') }}
        </span>
        <TrainingSolveActions
          :penalty="solve.penalty"
          @penalty="(penalty) => emit('penalty', solve.at, penalty)"
          @remove="emit('remove', solve, number)"
        />
      </li>
    </ol>
    <button
      v-if="!showAll && solves.length > VISIBLE"
      type="button"
      class="solve-list__more"
      @click="showAll = true"
    >
      Все {{ solves.length }} сборок
    </button>
  </div>
</template>

<style scoped>
.solve-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.solve-list__items {
  display: flex;
  flex-direction: column;
  padding: 0;
  list-style: none;
}

.solve-list__row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
}

.solve-list__row:last-child {
  border-bottom: none;
}

.solve-list__number {
  min-width: 36px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.solve-list__time {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--font-size-time-small);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.solve-list__time--dnf {
  color: var(--color-dnf);
}

.solve-list__more {
  align-self: center;
  padding: var(--space-2);
  background: none;
  border: none;
  color: var(--color-primary);
  font: inherit;
  font-weight: var(--font-weight-label);
  cursor: pointer;
}
</style>

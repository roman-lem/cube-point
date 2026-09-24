<script setup lang="ts">
import { AppIcon } from '@/shared/ui'
import type { TrainingPenalty } from '../model/session'

// Кнопки +2, DNF и удаления у сборки. +2 и DNF — переключатели:
// повторное нажатие снимает штраф. Удаление подтверждает страница.
const { penalty } = defineProps<{ penalty: TrainingPenalty }>()

const emit = defineEmits<{
  penalty: [penalty: TrainingPenalty]
  remove: []
}>()

function toggle(value: TrainingPenalty) {
  emit('penalty', penalty === value ? 'none' : value)
}
</script>

<template>
  <div class="solve-actions" role="group" aria-label="Штраф и удаление">
    <button
      type="button"
      :class="['solve-actions__button', { 'solve-actions__button--active': penalty === 'plus2' }]"
      :aria-pressed="penalty === 'plus2'"
      @click="toggle('plus2')"
    >
      +2
    </button>
    <button
      type="button"
      :class="[
        'solve-actions__button',
        'solve-actions__button--dnf',
        { 'solve-actions__button--active': penalty === 'dnf' },
      ]"
      :aria-pressed="penalty === 'dnf'"
      @click="toggle('dnf')"
    >
      DNF
    </button>
    <button
      type="button"
      class="solve-actions__button solve-actions__button--icon"
      aria-label="Удалить сборку"
      @click="emit('remove')"
    >
      <AppIcon name="delete" :size="18" />
    </button>
  </div>
</template>

<style scoped>
.solve-actions {
  display: flex;
  gap: var(--space-1);
}

.solve-actions__button {
  min-width: 40px;
  height: 32px;
  padding: 0 var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-badge);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.solve-actions__button--icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.solve-actions__button--active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.solve-actions__button--dnf.solve-actions__button--active {
  border-color: var(--color-dnf);
  color: var(--color-dnf);
}
</style>

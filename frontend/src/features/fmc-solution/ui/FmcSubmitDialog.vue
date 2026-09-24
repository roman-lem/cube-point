<script setup lang="ts">
import { computed } from 'vue'
import type { FmcAttemptState } from '@/entities/series'
import { ConfirmDialog } from '@/shared/ui'
import { formatCountdown } from '../model/clock'

// Второй шаг сдачи (макет fmc_submit): замороженное решение и время сдачи.
// «Вернуться к решению» снимает заморозку, после дедлайна его нет.
const open = defineModel<boolean>('open', { required: true })

const { state, timeOver = false, loading = false } = defineProps<{
  state: FmcAttemptState
  timeOver?: boolean
  loading?: boolean
  error?: string
}>()

const emit = defineEmits<{ confirm: []; back: [] }>()

// Время от старта до заморозки.
const submittedAfter = computed(() =>
  state.frozen_at
    ? formatCountdown(Date.parse(state.frozen_at) - Date.parse(state.started_at))
    : '',
)
</script>

<template>
  <ConfirmDialog
    v-model:open="open"
    title="Сдать решение?"
    confirm-label="Сдать"
    cancel-label="Вернуться к решению"
    :cancelable="!timeOver"
    :loading="loading"
    @confirm="emit('confirm')"
    @cancel="emit('back')"
  >
    <p>Проверьте решение: после сдачи изменить его будет нельзя. Время сдачи уже зафиксировано.</p>
    <div class="fmc-submit__solution">
      <span class="fmc-submit__label">Записанное решение</span>
      <p class="fmc-submit__moves">{{ state.frozen_solution || 'Решение пустое' }}</p>
      <div class="fmc-submit__time">
        <span>Время сдачи</span>
        <span class="fmc-submit__time-value">{{ submittedAfter }}</span>
      </div>
    </div>
    <p v-if="error" class="fmc-submit__error">{{ error }}</p>
  </ConfirmDialog>
</template>

<style scoped>
.fmc-submit__solution {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding: var(--space-3);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.fmc-submit__label {
  font-size: 12px;
  font-weight: var(--font-weight-label);
  text-transform: uppercase;
}

.fmc-submit__moves {
  margin: 0;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--font-size-time-small);
  word-spacing: 0.3em;
}

.fmc-submit__time {
  display: flex;
  justify-content: space-between;
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
  font-size: var(--font-size-label);
}

.fmc-submit__time-value {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-time-large);
}

.fmc-submit__error {
  margin-top: var(--space-2);
  color: var(--color-danger);
}
</style>

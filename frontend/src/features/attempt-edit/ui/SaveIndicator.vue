<script setup lang="ts">
import { AppIcon } from '@/shared/ui'
import type { CellState } from '../model/useAttemptSaving'

// Состояние сохранения ячейки или поля: сохраняется, сохранено, ошибка с повтором.
defineProps<{ state?: CellState }>()
</script>

<template>
  <span class="save-indicator" aria-live="polite">
    <span
      v-if="state?.status === 'saving'"
      class="save-indicator__spinner"
      role="status"
      aria-label="Сохраняется"
    />
    <span
      v-else-if="state?.status === 'saved'"
      class="save-indicator__saved"
      role="status"
      aria-label="Сохранено"
    >
      <AppIcon name="check" :size="16" />
    </span>
    <button
      v-else-if="state?.status === 'error' && state.retry"
      type="button"
      class="save-indicator__error"
      :title="`${state.message} — нажмите, чтобы повторить`"
      :aria-label="`${state.message}. Повторить`"
      @mousedown.prevent
      @click.stop="state.retry()"
    >
      <AppIcon name="refresh" :size="16" />
    </button>
    <span
      v-else-if="state?.status === 'error'"
      class="save-indicator__error"
      role="alert"
      :title="state.message"
      :aria-label="state.message"
    >
      <AppIcon name="error" :size="16" />
    </span>
  </span>
</template>

<style scoped>
.save-indicator {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.save-indicator__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: save-indicator-spin 0.8s linear infinite;
}

.save-indicator__saved {
  display: inline-flex;
  color: var(--color-personal-best);
}

.save-indicator__error {
  display: inline-flex;
  padding: 0;
  background: none;
  border: none;
  color: var(--color-danger);
  cursor: pointer;
}

@keyframes save-indicator-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { formatAttempt, type Attempt, type ResultType } from '@/shared/lib'
import {
  attemptToText, parseAttemptText, sameAttempt, toggleDnf, togglePlus2,
} from '../model/attemptText'
import { INVALID_INPUT_MESSAGE, type CellState } from '../model/useAttemptSaving'
import SaveIndicator from './SaveIndicator.vue'

// Attempt field for manual entry on a phone.
// Saves itself: on blur, on Enter and on the +2 / DNF buttons.
// An empty field erases the attempt (the server allows erasing only the last one and only
// one entered by the organizer).
const { attempt, resultType, disabled = false, state } = defineProps<{
  number: number
  attempt: Attempt | null
  resultType: ResultType
  /** Previous attempts are not entered yet. */
  disabled?: boolean
  state?: CellState
  /** FMC solution text, read-only. */
  solution?: string
  /** The attempt was corrected: a link to the edit history. */
  edited?: boolean
}>()
const emit = defineEmits<{ save: [attempt: Attempt | null]; history: [] }>()

const text = ref('')
const focused = ref(false)
const invalid = ref(false)

// While the field is focused, fresh data from the server does not overwrite the input.
watch(
  () => attempt,
  () => {
    if (!focused.value) {
      text.value = attemptToText(attempt, resultType)
    }
  },
  { immediate: true },
)

const current = computed(() => parseAttemptText(text.value, resultType) ?? attempt)

const hint = computed(() => {
  if (invalid.value) {
    return INVALID_INPUT_MESSAGE
  }
  if (state?.status === 'error') {
    return state.message
  }
  if (state?.status === 'saving') {
    return 'Сохраняется…'
  }
  if (disabled) {
    return 'Сначала предыдущие попытки'
  }
  return attempt ? formatAttempt(attempt, resultType) : 'Ожидание ввода'
})

function commit() {
  const trimmed = text.value.trim()
  if (!trimmed) {
    invalid.value = false
    if (attempt) {
      emit('save', null)
    }
    return
  }
  const parsed = parseAttemptText(trimmed, resultType)
  invalid.value = parsed === null
  if (parsed && !sameAttempt(parsed, attempt)) {
    emit('save', parsed)
  }
}

function onBlur() {
  focused.value = false
  commit()
}

function applyPenalty(next: Attempt | null) {
  if (next) {
    invalid.value = false
    text.value = attemptToText(next, resultType)
    emit('save', next)
  }
}
</script>

<template>
  <div :class="['attempt-field', { 'attempt-field--disabled': disabled }]">
    <div class="attempt-field__head">
      <label class="attempt-field__label" :for="`attempt-${number}`">Попытка {{ number }}</label>
      <button v-if="edited" type="button" class="attempt-field__history" @click="emit('history')">
        Исправлено · история
      </button>
      <SaveIndicator class="attempt-field__state" :state="state" />
    </div>
    <div class="attempt-field__row">
      <input
        :id="`attempt-${number}`"
        v-model="text"
        :class="['attempt-field__input', { 'attempt-field__input--error': invalid || state?.status === 'error' }]"
        :disabled="disabled"
        :inputmode="resultType === 'moves' ? 'numeric' : 'decimal'"
        autocomplete="off"
        :placeholder="resultType === 'moves' ? 'ходы' : '0.00'"
        @focus="focused = true"
        @blur="onBlur"
        @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
      />
      <button
        v-if="resultType === 'time'"
        type="button"
        :class="['attempt-field__penalty', { 'attempt-field__penalty--on': current?.penalty === 'plus2' }]"
        :disabled="disabled || current?.value == null"
        :aria-pressed="current?.penalty === 'plus2'"
        @click="applyPenalty(togglePlus2(current))"
      >
        +2
      </button>
      <button
        type="button"
        :class="['attempt-field__penalty', 'attempt-field__penalty--dnf', { 'attempt-field__penalty--on': current?.penalty === 'dnf' }]"
        :disabled="disabled"
        :aria-pressed="current?.penalty === 'dnf'"
        @click="applyPenalty(toggleDnf(current))"
      >
        DNF
      </button>
    </div>
    <p :class="['attempt-field__hint', { 'attempt-field__hint--error': invalid || state?.status === 'error' }]">
      {{ hint }}
      <button
        v-if="state?.status === 'error' && state.retry"
        type="button"
        class="attempt-field__retry"
        @click="state.retry()"
      >
        Повторить
      </button>
    </p>
    <p v-if="solution" class="attempt-field__solution">{{ solution }}</p>
  </div>
</template>

<style scoped>
.attempt-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.attempt-field--disabled {
  opacity: 0.6;
}

.attempt-field__head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.attempt-field__history {
  padding: 0;
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.attempt-field__state {
  margin-left: auto;
}

.attempt-field__label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.attempt-field__row {
  display: flex;
  gap: var(--space-2);
}

.attempt-field__input {
  flex: 1;
  min-width: 0;
  height: var(--control-height);
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  outline: none;
  font-family: var(--font-mono);
  font-size: var(--font-size-time-large);
  font-variant-numeric: tabular-nums;
}

.attempt-field__input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.attempt-field__input--error,
.attempt-field__input--error:focus {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 1px var(--color-danger);
}

.attempt-field__penalty {
  min-width: 56px;
  height: var(--control-height);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.attempt-field__penalty:disabled {
  cursor: default;
  opacity: 0.5;
}

.attempt-field__penalty--on {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
}

.attempt-field__penalty--dnf.attempt-field__penalty--on {
  background: var(--color-dnf);
  border-color: var(--color-dnf);
}

.attempt-field__hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.attempt-field__hint--error {
  color: var(--color-danger);
}

.attempt-field__retry {
  margin-left: var(--space-2);
  padding: 0;
  background: none;
  border: none;
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.attempt-field__solution {
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  overflow-wrap: anywhere;
}
</style>

<script setup lang="ts" generic="T extends string">
import { useId } from 'vue'

const model = defineModel<T>({ required: true })

defineProps<{
  options: { value: T; label: string }[]
  /** Подпись над полем. Без неё нужен ariaLabel. */
  label?: string
  ariaLabel?: string
  error?: string
  disabled?: boolean
}>()

const id = useId()
</script>

<template>
  <div class="app-select">
    <label v-if="label" class="app-select__label" :for="id">{{ label }}</label>
    <select
      :id="id"
      v-model="model"
      :class="['app-select__field', { 'app-select__field--error': error }]"
      :aria-label="label ? undefined : ariaLabel"
      :aria-invalid="Boolean(error)"
      :disabled="disabled"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <p v-if="error" class="app-select__error">{{ error }}</p>
  </div>
</template>

<style scoped>
.app-select {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.app-select__label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.app-select__field {
  width: 100%;
  height: var(--control-height);
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  outline: none;
}

.app-select__field:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.app-select__field:disabled {
  background: var(--color-background);
  color: var(--color-text-secondary);
}

.app-select__field--error {
  border-color: var(--color-danger);
}

.app-select__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}
</style>

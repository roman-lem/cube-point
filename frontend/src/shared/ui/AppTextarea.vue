<script setup lang="ts">
import { useId } from 'vue'

const model = defineModel<string>({ required: true })

const { rows = 4 } = defineProps<{
  label: string
  error?: string
  rows?: number
}>()

const id = useId()
</script>

<template>
  <div class="app-textarea">
    <label class="app-textarea__label" :for="id">{{ label }}</label>
    <textarea
      :id="id"
      v-model="model"
      :rows="rows"
      :class="['app-textarea__field', { 'app-textarea__field--error': error }]"
      :aria-invalid="Boolean(error)"
    />
    <p v-if="error" class="app-textarea__error">{{ error }}</p>
  </div>
</template>

<style scoped>
.app-textarea {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.app-textarea__label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.app-textarea__field {
  width: 100%;
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  outline: none;
  resize: vertical;
}

.app-textarea__field:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.app-textarea__field--error {
  border-color: var(--color-danger);
}

.app-textarea__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}
</style>

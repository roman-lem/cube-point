<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import AppIcon from './AppIcon.vue'

const model = defineModel<string>({ required: true })

const { type = 'text' } = defineProps<{
  label: string
  type?: 'text' | 'password' | 'email' | 'date' | 'time'
  /** Ошибка под полем. Пока она есть, подсказка не показывается. */
  error?: string
  hint?: string
  placeholder?: string
  autocomplete?: string
  /** Для type="date": минимальная дата YYYY-MM-DD. */
  min?: string
}>()

const id = useId()
const passwordVisible = ref(false)
const inputType = computed(() => (type === 'password' && passwordVisible.value ? 'text' : type))
</script>

<template>
  <div class="app-input">
    <label class="app-input__label" :for="id">{{ label }}</label>
    <div class="app-input__control">
      <input
        :id="id"
        v-model="model"
        :class="['app-input__field', { 'app-input__field--error': error }]"
        :type="inputType"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :min="min"
        :aria-invalid="Boolean(error)"
        :aria-describedby="error || hint ? `${id}-note` : undefined"
      />
      <button
        v-if="type === 'password'"
        type="button"
        class="app-input__toggle"
        :aria-label="passwordVisible ? 'Скрыть пароль' : 'Показать пароль'"
        @click="passwordVisible = !passwordVisible"
      >
        <AppIcon :name="passwordVisible ? 'visibility-off' : 'visibility'" :size="20" />
      </button>
    </div>
    <p v-if="error" :id="`${id}-note`" class="app-input__error">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-note`" class="app-input__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.app-input {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.app-input__label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.app-input__control {
  position: relative;
}

.app-input__field {
  width: 100%;
  height: var(--control-height);
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  outline: none;
}

/* Место под кнопку «глаз». */
.app-input__control:has(.app-input__toggle) .app-input__field {
  padding-right: var(--control-height);
}

.app-input__field::placeholder {
  color: var(--color-text-secondary);
}

.app-input__field:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.app-input__field--error,
.app-input__field--error:focus {
  border-color: var(--color-danger);
  box-shadow: 0 0 0 1px var(--color-danger);
}

.app-input__toggle {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--control-height);
  height: var(--control-height);
  padding: 0;
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.app-input__error,
.app-input__hint {
  font-size: var(--font-size-label);
}

.app-input__error {
  color: var(--color-danger);
}

.app-input__hint {
  color: var(--color-text-secondary);
}
</style>

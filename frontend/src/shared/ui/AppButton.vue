<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

const {
  variant = 'primary',
  type = 'button',
  loading = false,
  disabled = false,
} = defineProps<{
  variant?: 'primary' | 'secondary' | 'danger'
  type?: 'button' | 'submit'
  /** Идёт запрос: кнопка неактивна, чтобы не отправить форму дважды. */
  loading?: boolean
  disabled?: boolean
  /** Кнопка-ссылка на страницу приложения. */
  to?: RouteLocationRaw
}>()
</script>

<template>
  <RouterLink v-if="to" :to="to" :class="['app-button', `app-button--${variant}`]">
    <slot />
  </RouterLink>
  <button
    v-else
    :type="type"
    :class="['app-button', `app-button--${variant}`]"
    :disabled="disabled || loading"
    :aria-busy="loading"
  >
    <slot />
  </button>
</template>

<style scoped>
.app-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: var(--control-height);
  padding: 0 var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--radius-button);
  font-weight: var(--font-weight-label);
  text-decoration: none;
  cursor: pointer;
  transition: opacity 0.15s;
}

.app-button:disabled {
  opacity: 0.6;
  cursor: default;
}

.app-button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.app-button--primary {
  background: var(--color-primary);
  color: var(--color-on-primary);
}

.app-button--secondary {
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-text-primary);
}

.app-button--danger {
  background: var(--color-surface);
  border-color: var(--color-danger);
  color: var(--color-danger);
}
</style>

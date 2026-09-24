<script setup lang="ts">
import AppIcon from './AppIcon.vue'

// Общая ошибка формы, не относящаяся к одному полю («Неверный логин или пароль»).
defineProps<{ message: string }>()
</script>

<template>
  <p class="form-error" role="alert">
    <AppIcon name="error" :size="18" />
    <span>{{ message }}</span>
  </p>
</template>

<style scoped>
.form-error {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface));
  border-radius: var(--radius-button);
  color: var(--color-danger);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.form-error svg {
  flex-shrink: 0;
  margin-top: 1px;
}
</style>

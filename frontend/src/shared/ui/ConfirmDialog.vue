<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import AppButton from './AppButton.vue'

// Диалог подтверждения поверх страницы (нативный <dialog>).
const open = defineModel<boolean>('open', { required: true })

const { confirmLabel = 'Подтвердить', danger = false, loading = false } = defineProps<{
  title: string
  confirmLabel?: string
  /** Опасное действие: кнопка подтверждения в стиле danger. */
  danger?: boolean
  /** Идёт запрос: кнопки неактивны, закрыть диалог нельзя. */
  loading?: boolean
}>()

const emit = defineEmits<{ confirm: [] }>()

const dialog = ref<HTMLDialogElement>()

function sync(value: boolean) {
  if (value && !dialog.value?.open) {
    dialog.value?.showModal()
  } else if (!value) {
    dialog.value?.close()
  }
}

watch(open, sync)
onMounted(() => sync(open.value))

// Esc и клик по фону закрывают диалог, если не идёт запрос.
function onCancel(event: Event) {
  event.preventDefault()
  if (!loading) {
    open.value = false
  }
}

function onBackdropClick(event: MouseEvent) {
  if (event.target === dialog.value) {
    onCancel(event)
  }
}
</script>

<template>
  <dialog ref="dialog" class="confirm-dialog" @cancel="onCancel" @click="onBackdropClick">
    <div class="confirm-dialog__body">
      <h2 class="confirm-dialog__title">{{ title }}</h2>
      <div class="confirm-dialog__text">
        <slot />
      </div>
      <div class="confirm-dialog__actions">
        <AppButton :variant="danger ? 'danger' : 'primary'" :loading="loading" @click="emit('confirm')">
          {{ confirmLabel }}
        </AppButton>
        <AppButton variant="secondary" :disabled="loading" @click="open = false">Отмена</AppButton>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.confirm-dialog {
  width: calc(100% - 2 * var(--page-padding));
  max-width: 400px;
  padding: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: inherit;
}

.confirm-dialog::backdrop {
  background: color-mix(in srgb, var(--color-text-primary) 40%, transparent);
}

.confirm-dialog__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-4) var(--space-4);
}

.confirm-dialog__title {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.confirm-dialog__text {
  color: var(--color-text-secondary);
}

.confirm-dialog__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
</style>

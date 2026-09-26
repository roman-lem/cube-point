<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import AppButton from './AppButton.vue'

// Confirmation dialog over the page (native <dialog>).
const open = defineModel<boolean>('open', { required: true })

const {
  confirmLabel = 'Подтвердить',
  cancelLabel = 'Отмена',
  cancelable = true,
  danger = false,
  loading = false,
  confirmDisabled = false,
  wide = false,
} = defineProps<{
  title: string
  confirmLabel?: string
  cancelLabel?: string
  /** false: the dialog can be closed only by confirming. */
  cancelable?: boolean
  /** Dangerous action: the confirm button uses the danger style. */
  danger?: boolean
  /** A request is in flight: the buttons are disabled and the dialog cannot be closed. */
  loading?: boolean
  /** Confirming is not possible yet (e.g. not everything in the dialog is resolved). */
  confirmDisabled?: boolean
  /** A wide dialog for content with lists. */
  wide?: boolean
}>()

const emit = defineEmits<{ confirm: []; cancel: [] }>()

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

// Esc, a click on the backdrop and the cancel button close the dialog unless a request is in flight.
function cancel() {
  if (!loading && cancelable) {
    open.value = false
    emit('cancel')
  }
}

function onCancel(event: Event) {
  event.preventDefault()
  cancel()
}

function onBackdropClick(event: MouseEvent) {
  if (event.target === dialog.value) {
    onCancel(event)
  }
}
</script>

<template>
  <dialog
    ref="dialog"
    :class="['confirm-dialog', { 'confirm-dialog--wide': wide }]"
    @cancel="onCancel" @click="onBackdropClick">
    <div class="confirm-dialog__body">
      <h2 class="confirm-dialog__title">{{ title }}</h2>
      <div class="confirm-dialog__text">
        <slot />
      </div>
      <div class="confirm-dialog__actions">
        <AppButton
          :variant="danger ? 'danger' : 'primary'"
          :loading="loading"
          :disabled="confirmDisabled"
          @click="emit('confirm')"
        >
          {{ confirmLabel }}
        </AppButton>
        <AppButton v-if="cancelable" variant="secondary" :disabled="loading" @click="cancel">
          {{ cancelLabel }}
        </AppButton>
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

.confirm-dialog--wide {
  max-width: 560px;
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

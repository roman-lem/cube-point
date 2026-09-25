<script setup lang="ts">
import { ref } from 'vue'
import { ApiError, http } from '@/shared/api'
import { AppButton, AppIcon, AppTextarea, ConfirmDialog } from '@/shared/ui'

// Дисквалификация участника на встрече: с обязательной причиной и возможностью отмены.
// Результаты участника уходят из таблиц и рекордов, серии остаются.
const { meetupId, user, disqualification, compact = false } = defineProps<{
  meetupId: number
  user: { id: number; display_name: string }
  disqualification: { reason: string } | null
  /** Только иконка вместо кнопки с текстом (строка списка участников). */
  compact?: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const disqualifyOpen = ref(false)
const cancelOpen = ref(false)
const reason = ref('')
const reasonError = ref('')
const loading = ref(false)
const error = ref('')

const url = () => `/api/meetups/${meetupId}/participants/${user.id}/disqualification`

function openDisqualify() {
  reason.value = ''
  reasonError.value = ''
  error.value = ''
  disqualifyOpen.value = true
}

async function run(action: () => Promise<unknown>, close: () => void) {
  loading.value = true
  error.value = ''
  try {
    await action()
    close()
    emit('changed')
  } catch (e) {
    if (e instanceof ApiError && e.fields.reason) {
      reasonError.value = e.fields.reason
    } else {
      error.value = e instanceof ApiError ? e.message : 'Не удалось сохранить'
    }
  } finally {
    loading.value = false
  }
}

function disqualify() {
  if (!reason.value.trim()) {
    reasonError.value = 'Укажите причину'
    return
  }
  return run(
    () => http.put(url(), { reason: reason.value }),
    () => (disqualifyOpen.value = false),
  )
}

function cancel() {
  return run(() => http.delete(url()), () => (cancelOpen.value = false))
}
</script>

<template>
  <div class="disqualification">
    <template v-if="disqualification">
      <span class="disqualification__badge" :title="disqualification.reason">Дисквалифицирован</span>
      <button type="button" class="disqualification__link" @click="cancelOpen = true">
        Отменить
      </button>
    </template>
    <button
      v-else-if="compact"
      type="button"
      class="disqualification__icon"
      :aria-label="`Дисквалифицировать: ${user.display_name}`"
      title="Дисквалифицировать"
      @click="openDisqualify"
    >
      <AppIcon name="block" :size="20" />
    </button>
    <AppButton v-else variant="danger" @click="openDisqualify">
      <AppIcon name="block" :size="20" />
      Дисквалифицировать
    </AppButton>

    <ConfirmDialog
      v-model:open="disqualifyOpen"
      title="Дисквалифицировать участника?"
      confirm-label="Дисквалифицировать"
      danger
      :loading="loading"
      @confirm="disqualify"
    >
      <div class="disqualification__form">
        <p>
          Все результаты участника «{{ user.display_name }}» на этой встрече уйдут из таблиц
          и рекордов. Серии сохранятся, дисквалификацию можно отменить.
        </p>
        <AppTextarea v-model="reason" label="Причина" :rows="3" :error="reasonError" />
        <p v-if="error" class="disqualification__error" role="alert">{{ error }}</p>
      </div>
    </ConfirmDialog>

    <ConfirmDialog
      v-model:open="cancelOpen"
      title="Отменить дисквалификацию?"
      confirm-label="Отменить дисквалификацию"
      cancel-label="Назад"
      :loading="loading"
      @confirm="cancel"
    >
      <p>Результаты участника «{{ user.display_name }}» вернутся в таблицы и рекорды.</p>
      <p v-if="disqualification">Причина: {{ disqualification.reason }}</p>
      <p v-if="error" class="disqualification__error" role="alert">{{ error }}</p>
    </ConfirmDialog>
  </div>
</template>

<style scoped>
.disqualification {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.disqualification__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-text-primary);
}

.disqualification__badge {
  padding: 2px var(--space-2);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-badge);
  color: var(--color-danger);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.disqualification__link {
  padding: 0;
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.disqualification__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--control-height);
  height: var(--control-height);
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-button);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.disqualification__icon:hover {
  color: var(--color-danger);
}

.disqualification__error {
  color: var(--color-danger);
}
</style>

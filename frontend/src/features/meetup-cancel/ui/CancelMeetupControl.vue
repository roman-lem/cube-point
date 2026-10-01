<script setup lang="ts">
import { ref } from 'vue'
import type { Meetup } from '@/entities/meetup'
import { ApiError, http } from '@/shared/api'
import { AppButton, AppCard, ConfirmDialog, SettingRow } from '@/shared/ui'

// Cancelling a meetup by the organizer: only before the first result
// (restriction from the server). The meetup stays in the club list as cancelled,
// requests and scrambles are deleted, the join link stops working.
const { meetup } = defineProps<{ meetup: Meetup }>()
const emit = defineEmits<{ cancelled: [meetup: Meetup]; failed: [] }>()

const open = ref(false)
const loading = ref(false)
const error = ref('')

function openDialog() {
  error.value = ''
  open.value = true
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const result = await http.post<{ meetup: Meetup }>(`/api/meetups/${meetup.id}/cancel`)
    open.value = false
    emit('cancelled', result.meetup)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось отменить встречу'
    // Someone may have submitted an attempt meanwhile: the restriction is reloaded.
    emit('failed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppCard>
    <SettingRow
      title="Отменить встречу"
      description="Встреча останется в списке клуба с пометкой «Отменена». Заявки и скрамблы удалятся, ссылка и QR-код перестанут работать."
      :restriction="meetup.cancel_restriction ?? null"
    >
      <AppButton variant="danger" :disabled="Boolean(meetup.cancel_restriction)" @click="openDialog">
        Отменить встречу
      </AppButton>
    </SettingRow>
  </AppCard>

  <ConfirmDialog
    v-model:open="open"
    title="Отменить встречу?"
    confirm-label="Отменить встречу"
    cancel-label="Не отменять"
    danger
    :loading="loading"
    @confirm="submit"
  >
    <div class="cancel-meetup__body">
      <p>
        Вернуть встречу будет нельзя. Заявки на участие и скрамблы удалятся, ссылка и QR-код
        перестанут работать.
      </p>
      <p v-if="error" class="cancel-meetup__error" role="alert">{{ error }}</p>
    </div>
  </ConfirmDialog>
</template>

<style scoped>
.cancel-meetup__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-text-primary);
}

.cancel-meetup__error {
  color: var(--color-danger);
}
</style>

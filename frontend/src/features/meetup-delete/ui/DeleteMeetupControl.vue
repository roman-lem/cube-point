<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError } from '@/shared/api'
import { plural } from '@/shared/lib'
import { AppButton, AppCard, ConfirmDialog, SettingRow } from '@/shared/ui'
import { deleteMeetup, fetchMeetupDeletion, type MeetupDeletion } from '../api/deleteMeetup'

// Deleting a meetup by the administrator: events, scrambles, requests, results and
// disqualifications go, club records are recalculated. Not possible while the meetup
// is live (restriction from the server). What will be deleted is shown in the dialog.
const { meetupId, status } = defineProps<{ meetupId: number; status: string }>()
const emit = defineEmits<{ deleted: [] }>()

const summary = ref<MeetupDeletion | null>(null)
const open = ref(false)
const error = ref('')
const loading = ref(false)

async function load() {
  try {
    summary.value = await fetchMeetupDeletion(meetupId)
    error.value = ''
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить данные встречи'
  }
}

// The status changes on auto-refresh of the page: the restriction goes with it.
watch(() => [meetupId, status], load, { immediate: true })

async function openDialog() {
  error.value = ''
  open.value = true
  // The numbers could have changed since the page was opened.
  await load()
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await deleteMeetup(meetupId)
    open.value = false
    emit('deleted')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось удалить встречу'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppCard class="delete-meetup">
    <h2 class="delete-meetup__heading">Опасная зона</h2>
    <SettingRow
      title="Удалить встречу"
      description="Результаты, заявки и скрамблы встречи будут удалены, рекорды клуба пересчитаются."
      :restriction="summary?.delete_restriction ?? null"
    >
      <AppButton
        variant="danger"
        :disabled="!summary || Boolean(summary.delete_restriction)"
        @click="openDialog"
      >
        Удалить встречу
      </AppButton>
    </SettingRow>
    <p v-if="error && !open" class="delete-meetup__error" role="alert">{{ error }}</p>
  </AppCard>

  <ConfirmDialog
    v-model:open="open"
    title="Удалить встречу?"
    confirm-label="Удалить навсегда"
    danger
    :loading="loading"
    :confirm-disabled="!summary || Boolean(summary.delete_restriction)"
    @confirm="submit"
  >
    <div class="delete-meetup__body">
      <p>Восстановить встречу будет нельзя. Вместе с ней удалятся:</p>
      <ul v-if="summary" class="delete-meetup__list">
        <li>
          {{ plural(summary.deletion.results, ['результат', 'результата', 'результатов']) }}
          у {{ plural(summary.deletion.participants, ['участника', 'участников', 'участников']) }}
          с историей правок и дисквалификации;
        </li>
        <li>{{ plural(summary.deletion.requests, ['заявка', 'заявки', 'заявок']) }} на участие;</li>
        <li>дисциплины и скрамблы встречи.</li>
      </ul>
      <p>
        Рекорды клуба пересчитаются по остальным встречам, личные рекорды участников — по
        остальным результатам. Аккаунты участников останутся.
      </p>
      <p v-if="summary?.delete_restriction" class="delete-meetup__error">
        {{ summary.delete_restriction }}
      </p>
      <p v-if="error" class="delete-meetup__error" role="alert">{{ error }}</p>
    </div>
  </ConfirmDialog>
</template>

<style scoped>
.delete-meetup {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.delete-meetup__heading {
  color: var(--color-danger);
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.delete-meetup__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-text-primary);
}

.delete-meetup__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding-left: var(--space-5);
  list-style: disc;
}

.delete-meetup__error {
  color: var(--color-danger);
}
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ClubMemberCard } from '@/entities/club'
import { ApiError } from '@/shared/api'
import { formatDate, formatDateTime } from '@/shared/lib'
import { AppButton, AppIcon, AppTextarea, ConfirmDialog, SettingRow } from '@/shared/ui'
import { banMember, unbanMember } from '../api/banApi'

// Club ban with a required reason, and unbanning. A ban applies
// to the future: past results and records stay. At a live meetup the participant
// stops submitting attempts immediately; already submitted ones stay.
const { clubId, member, timeZone } = defineProps<{
  clubId: number
  member: ClubMemberCard
  timeZone: string
}>()
const emit = defineEmits<{ changed: [member: ClubMemberCard] }>()

const bannedSince = computed(() => {
  const ban = member.ban
  if (!ban) {
    return ''
  }
  const since = `С ${formatDateTime(ban.banned_at, timeZone)}`
  return ban.banned_by ? `${since}, заблокировал(а) ${ban.banned_by.display_name}` : since
})

const banOpen = ref(false)
const unbanOpen = ref(false)
const reason = ref('')
const reasonError = ref('')
const loading = ref(false)
const error = ref('')

function openBan() {
  reason.value = ''
  reasonError.value = ''
  error.value = ''
  banOpen.value = true
}

function openUnban() {
  error.value = ''
  unbanOpen.value = true
}

async function run(action: () => Promise<ClubMemberCard>, close: () => void) {
  loading.value = true
  error.value = ''
  try {
    emit('changed', await action())
    close()
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

function ban() {
  if (!reason.value.trim()) {
    reasonError.value = 'Укажите причину'
    return
  }
  return run(
    () => banMember(clubId, member.user.id, reason.value),
    () => (banOpen.value = false),
  )
}

function unban() {
  return run(() => unbanMember(clubId, member.user.id), () => (unbanOpen.value = false))
}
</script>

<template>
  <SettingRow
    v-if="member.ban"
    title="Заблокирован в клубе"
    :description="bannedSince"
  >
    <template #details>
      <p class="ban-control__reason">Причина: {{ member.ban.reason }}</p>
    </template>
    <AppButton variant="secondary" @click="openUnban">Разблокировать</AppButton>
  </SettingRow>

  <SettingRow
    v-else
    title="Заблокировать в клубе"
    description="Запрещает подавать заявки и участвовать в будущих встречах клуба. Прошлые результаты и рекорды остаются."
    :restriction="member.restrictions.ban"
  >
    <AppButton variant="danger" :disabled="member.restrictions.ban !== null" @click="openBan">
      <AppIcon name="block" :size="20" />
      Заблокировать
    </AppButton>
  </SettingRow>

  <ConfirmDialog
    v-model:open="banOpen"
    title="Заблокировать участника?"
    confirm-label="Заблокировать"
    danger
    :loading="loading"
    @confirm="ban"
  >
    <div class="ban-control__form">
      <p>
        «{{ member.user.display_name }}» не сможет подавать заявки на встречи клуба.
        Прошлые результаты и рекорды останутся.
      </p>
      <p v-if="member.live_meetup" class="ban-control__warning">
        Сейчас участвует во встрече {{ formatDate(member.live_meetup.date) }}: не сможет
        продолжить серии. Сданные попытки останутся; чтобы аннулировать их — дисквалификация.
      </p>
      <AppTextarea v-model="reason" label="Причина" :rows="3" :error="reasonError" />
      <p v-if="error" class="ban-control__error" role="alert">{{ error }}</p>
    </div>
  </ConfirmDialog>

  <ConfirmDialog
    v-model:open="unbanOpen"
    title="Разблокировать участника?"
    confirm-label="Разблокировать"
    cancel-label="Назад"
    :loading="loading"
    @confirm="unban"
  >
    <p>«{{ member.user.display_name }}» снова сможет подавать заявки на встречи клуба.</p>
    <p v-if="error" class="ban-control__error" role="alert">{{ error }}</p>
  </ConfirmDialog>
</template>

<style scoped>
.ban-control__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-text-primary);
}

.ban-control__warning {
  padding: var(--space-3);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-button);
}

.ban-control__reason {
  font-size: var(--font-size-label);
  overflow-wrap: anywhere;
}

.ban-control__error {
  color: var(--color-danger);
}
</style>

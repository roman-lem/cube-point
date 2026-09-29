<script setup lang="ts">
import { ref } from 'vue'
import type { Restriction, UserRef } from '@/entities/club'
import { ApiError } from '@/shared/api'
import { AppButton, AppIcon, ConfirmDialog, SettingRow, TemporaryPassword } from '@/shared/ui'
import { resetPassword } from '../api/resetPassword'

// Resetting a password: the temporary password is shown once, all of the user's
// sessions end. From the club member card (clubId) or from the administrator's
// user card (without clubId). An organizer's password is reset by the administrator.
const { clubId, user, restriction } = defineProps<{
  clubId?: number
  user: UserRef
  restriction: Restriction
}>()

const confirmOpen = ref(false)
const loading = ref(false)
const error = ref('')
const password = ref<string | null>(null)
const resultOpen = ref(false)

function ask() {
  error.value = ''
  confirmOpen.value = true
}

async function reset() {
  loading.value = true
  error.value = ''
  try {
    password.value = await resetPassword(user.id, clubId)
    confirmOpen.value = false
    resultOpen.value = true
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось сбросить пароль'
  } finally {
    loading.value = false
  }
}

function done() {
  resultOpen.value = false
  // The password is not shown anywhere else.
  password.value = null
}
</script>

<template>
  <SettingRow
    title="Сбросить пароль"
    description="Выдаёт временный пароль, он показывается один раз. Участника разлогинит на всех устройствах."
    :restriction="restriction"
  >
    <AppButton variant="secondary" :disabled="restriction !== null" @click="ask">
      <AppIcon name="lock" :size="20" />
      Сбросить пароль
    </AppButton>
  </SettingRow>

  <ConfirmDialog
    v-model:open="confirmOpen"
    title="Сбросить пароль?"
    confirm-label="Сбросить"
    :loading="loading"
    @confirm="reset"
  >
    <p>
      Текущий пароль участника «{{ user.display_name }}» перестанет работать, а все его
      сессии завершатся. При входе с временным паролем нужно будет задать новый.
    </p>
    <p v-if="error" class="password-reset__error" role="alert">{{ error }}</p>
  </ConfirmDialog>

  <ConfirmDialog
    v-model:open="resultOpen"
    title="Временный пароль"
    confirm-label="Готово"
    :cancelable="false"
    @confirm="done"
  >
    <div class="password-reset__result">
      <p>
        Передайте пароль участнику — <strong>он показывается один раз</strong>.
      </p>
      <TemporaryPassword v-if="password" :login="user.login" :password="password" />
    </div>
  </ConfirmDialog>
</template>

<style scoped>
.password-reset__result {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.password-reset__error {
  color: var(--color-danger);
}
</style>

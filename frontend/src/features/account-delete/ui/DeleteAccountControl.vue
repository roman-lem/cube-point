<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { AppButton, AppInput, ConfirmDialog, SettingRow } from '@/shared/ui'
import { deleteAccount } from '../api/deleteAccount'

// Удаление своего аккаунта с подтверждением паролем. Логин, почта, пароль
// и согласия уничтожаются, результаты остаются под именем «Удалённый участник».
// Последний организатор клуба сначала передаёт роль (restriction с сервера).
const emit = defineEmits<{ deleted: [] }>()

const userStore = useUserStore()
const open = ref(false)
const password = ref('')
const passwordError = ref('')
const error = ref('')
const loading = ref(false)

function openDialog() {
  password.value = ''
  passwordError.value = ''
  error.value = ''
  open.value = true
}

async function submit() {
  passwordError.value = ''
  error.value = ''
  if (!password.value) {
    passwordError.value = 'Введите пароль'
    return
  }
  loading.value = true
  try {
    await deleteAccount(password.value)
    open.value = false
    userStore.clear()
    emit('deleted')
  } catch (e) {
    if (e instanceof ApiError && e.fields.password) {
      passwordError.value = e.fields.password
    } else {
      error.value = e instanceof ApiError ? e.message : 'Не удалось удалить аккаунт'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <SettingRow
    title="Удалить аккаунт"
    description="Логин, пароль, почта и согласия будут удалены. Результаты и рекорды останутся под именем «Удалённый участник»."
    :restriction="userStore.user?.delete_restriction"
  >
    <AppButton
      variant="danger"
      :disabled="Boolean(userStore.user?.delete_restriction)"
      @click="openDialog"
    >
      Удалить аккаунт
    </AppButton>
  </SettingRow>

  <ConfirmDialog
    v-model:open="open"
    title="Удалить аккаунт?"
    confirm-label="Удалить навсегда"
    danger
    :loading="loading"
    @confirm="submit"
  >
    <form class="delete-account__form" @submit.prevent="submit">
      <p>
        Восстановить аккаунт будет нельзя. Вы выйдете из всех клубов и на всех устройствах.
        Результаты встреч и рекорды останутся в таблицах под именем «Удалённый участник».
      </p>
      <AppInput
        v-model="password"
        label="Пароль"
        type="password"
        autocomplete="current-password"
        :error="passwordError"
      />
      <p v-if="error" class="delete-account__error" role="alert">{{ error }}</p>
    </form>
  </ConfirmDialog>
</template>

<style scoped>
.delete-account__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  color: var(--color-text-primary);
}

.delete-account__error {
  color: var(--color-danger);
}
</style>

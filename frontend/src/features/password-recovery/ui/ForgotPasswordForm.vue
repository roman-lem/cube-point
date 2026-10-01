<script setup lang="ts">
import { ref } from 'vue'
import { useFormErrors } from '@/shared/lib'
import { AppButton, AppInput, FormError } from '@/shared/ui'
import { requestPasswordReset } from '../api/passwordRecoveryApi'

// The request for a reset link. The answer is the same whether the account exists
// and has an email or not: the page must not reveal someone else's login or email.
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const loginOrEmail = ref('')
const loading = ref(false)
const sent = ref(false)

async function submit() {
  clearErrors()
  if (!loginOrEmail.value.trim()) {
    fieldErrors.value = { login_or_email: 'Введите логин или почту' }
    return
  }
  loading.value = true
  try {
    await requestPasswordReset(loginOrEmail.value)
    sent.value = true
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <p v-if="sent" class="recovery-form__sent">
    Если у аккаунта есть подтверждённая почта, мы отправили на неё ссылку. Если почты нет —
    обратитесь к организатору своего клуба.
  </p>
  <form v-else class="recovery-form" novalidate @submit.prevent="submit">
    <AppInput
      v-model="loginOrEmail"
      label="Логин или почта"
      autocomplete="username"
      hint="Ссылку для восстановления пришлём на почту, привязанную к аккаунту"
      :error="fieldErrors.login_or_email"
    />
    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" class="recovery-form__submit" :loading="loading">Отправить ссылку</AppButton>
  </form>
</template>

<style scoped src="./recoveryForm.css"></style>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { useFormErrors } from '@/shared/lib'
import { AppButton, AppInput, FormError } from '@/shared/ui'
import { confirmPasswordReset } from '../api/passwordRecoveryApi'

// The new password by the link from the letter. After saving the user is logged in,
// sessions on other devices end.
const { token, login } = defineProps<{ token: string; login: string }>()
const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const form = ref({ new_password: '', new_password_repeat: '' })
const loading = ref(false)

async function submit() {
  clearErrors()
  if (form.value.new_password_repeat !== form.value.new_password) {
    fieldErrors.value = { new_password_repeat: 'Пароли не совпадают' }
    return
  }
  loading.value = true
  try {
    userStore.setUser(await confirmPasswordReset(token, form.value.new_password))
    emit('success')
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="recovery-form" novalidate @submit.prevent="submit">
    <!-- The login for the browser's password manager. -->
    <input type="text" name="username" autocomplete="username" :value="login" hidden />
    <AppInput
      v-model="form.new_password"
      label="Новый пароль"
      type="password"
      autocomplete="new-password"
      hint="Минимум 8 символов, не совпадает с логином и текущим паролем"
      :error="fieldErrors.new_password"
    />
    <AppInput
      v-model="form.new_password_repeat"
      label="Повторите новый пароль"
      type="password"
      autocomplete="new-password"
      :error="fieldErrors.new_password_repeat"
    />
    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" class="recovery-form__submit" :loading="loading">Сохранить и войти</AppButton>
  </form>
</template>

<style scoped src="./recoveryForm.css"></style>

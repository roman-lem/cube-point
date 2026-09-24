<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { AppButton, AppInput, FormError } from '@/shared/ui'
import { login } from '../api/authApi'
import { useFormErrors } from '../lib/useFormErrors'

const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const form = ref({ login: '', password: '', remember: true })
const loading = ref(false)

async function submit() {
  clearErrors()
  loading.value = true
  try {
    userStore.setUser(await login(form.value))
    emit('success')
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="auth-form" novalidate @submit.prevent="submit">
    <AppInput
      v-model="form.login"
      label="Логин"
      autocomplete="username"
      :error="fieldErrors.login"
    />
    <AppInput
      v-model="form.password"
      label="Пароль"
      type="password"
      autocomplete="current-password"
      :error="fieldErrors.password"
    />
    <FormError v-if="formError" :message="formError" />
    <label class="auth-form__checkbox">
      <input v-model="form.remember" type="checkbox" />
      Запомнить меня
    </label>
    <AppButton type="submit" class="auth-form__submit" :loading="loading">Войти</AppButton>
  </form>
</template>

<style scoped src="./authForm.css"></style>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { AppButton, AppInput, FormError } from '@/shared/ui'
import { register } from '../api/authApi'
import { useFormErrors } from '@/shared/lib'

const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const form = ref({ display_name: '', login: '', password: '', password_repeat: '' })
const loading = ref(false)

async function submit() {
  clearErrors()
  // Повтор пароля проверяем только здесь, на сервер он не отправляется.
  if (form.value.password_repeat !== form.value.password) {
    fieldErrors.value = { password_repeat: 'Пароли не совпадают' }
    return
  }

  loading.value = true
  try {
    const { display_name, login, password } = form.value
    userStore.setUser(await register({ display_name, login, password }))
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
      v-model="form.display_name"
      label="Имя и фамилия"
      placeholder="Алексей Смирнов"
      autocomplete="name"
      hint="Так вас увидят в таблицах результатов"
      :error="fieldErrors.display_name"
    />
    <AppInput
      v-model="form.login"
      label="Логин"
      placeholder="например, alex_cube"
      autocomplete="username"
      :error="fieldErrors.login"
    />
    <AppInput
      v-model="form.password"
      label="Пароль"
      type="password"
      autocomplete="new-password"
      hint="Минимум 8 символов"
      :error="fieldErrors.password"
    />
    <AppInput
      v-model="form.password_repeat"
      label="Повторите пароль"
      type="password"
      autocomplete="new-password"
      :error="fieldErrors.password_repeat"
    />
    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" class="auth-form__submit" :loading="loading">Создать аккаунт</AppButton>
  </form>
</template>

<style scoped src="./authForm.css"></style>

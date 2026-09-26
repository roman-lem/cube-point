<script setup lang="ts">
import { computed, ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { AppButton, AppInput, FormError } from '@/shared/ui'
import { changePassword } from '../api/authApi'
import { useFormErrors } from '@/shared/lib'

const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const form = ref({ current_password: '', new_password: '', new_password_repeat: '' })
const loading = ref(false)

// Logged in with a temporary password: the current password is not asked.
const forced = computed(() => userStore.user?.must_change_password ?? false)

async function submit() {
  clearErrors()
  if (form.value.new_password_repeat !== form.value.new_password) {
    fieldErrors.value = { new_password_repeat: 'Пароли не совпадают' }
    return
  }

  loading.value = true
  try {
    const { current_password, new_password } = form.value
    const user = await changePassword(
      forced.value ? { new_password } : { current_password, new_password },
    )
    userStore.setUser(user)
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
      v-if="!forced"
      v-model="form.current_password"
      label="Текущий пароль"
      type="password"
      autocomplete="current-password"
      :error="fieldErrors.current_password"
    />
    <AppInput
      v-model="form.new_password"
      label="Новый пароль"
      type="password"
      autocomplete="new-password"
      hint="Минимум 8 символов"
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
    <AppButton type="submit" class="auth-form__submit" :loading="loading">Сохранить пароль</AppButton>
  </form>
</template>

<style scoped src="./authForm.css"></style>

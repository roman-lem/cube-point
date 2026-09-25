<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { AppButton, AppInput, FormError } from '@/shared/ui'
import { fetchRegistrationOpen, register } from '../api/authApi'
import { missingConsents } from '../model/consents'
import { useFormErrors } from '@/shared/lib'
import ConsentFields from './ConsentFields.vue'

const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const form = ref({ display_name: '', login: '', password: '', password_repeat: '' })
const consents = ref({ processing: false, publication: false })
const loading = ref(false)

// Регистрацию можно закрыть на сервере (REGISTRATION_OPEN=0). Если статус
// не загрузился, форма остаётся: сервер всё равно проверит.
const registrationOpen = ref(true)
onMounted(async () => {
  registrationOpen.value = await fetchRegistrationOpen().catch(() => true)
})

async function submit() {
  clearErrors()
  // Повтор пароля проверяем только здесь, на сервер он не отправляется.
  const errors = missingConsents(consents.value)
  if (form.value.password_repeat !== form.value.password) {
    errors.password_repeat = 'Пароли не совпадают'
  }
  if (Object.keys(errors).length > 0) {
    fieldErrors.value = errors
    return
  }

  loading.value = true
  try {
    const { display_name, login, password } = form.value
    userStore.setUser(await register({ display_name, login, password, consents: consents.value }))
    emit('success')
  } catch (error) {
    if (error instanceof ApiError && error.code === 'registration_closed') {
      registrationOpen.value = false
    } else {
      showError(error)
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <p v-if="!registrationOpen" class="auth-form__closed">
    Регистрация скоро откроется. Если у вас уже есть аккаунт, войдите в него.
  </p>
  <form v-else class="auth-form" novalidate @submit.prevent="submit">
    <AppInput
      v-model="form.display_name"
      label="Имя или никнейм"
      placeholder="например, Алексей или alex_cube"
      autocomplete="nickname"
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
    <ConsentFields v-model="consents" :errors="fieldErrors" />
    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" class="auth-form__submit" :loading="loading">Создать аккаунт</AppButton>
  </form>
</template>

<style scoped src="./authForm.css"></style>

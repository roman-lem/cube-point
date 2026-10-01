<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { AppButton, AppInput, FormError } from '@/shared/ui'
import { fetchRegistration, register } from '../api/authApi'
import { emptyConsents, missingConsents } from '../model/consents'
import { useFormErrors } from '@/shared/lib'
import ConsentFields from './ConsentFields.vue'

const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const form = ref({ display_name: '', login: '', password: '', password_repeat: '' })
const consents = ref(emptyConsents())
const loading = ref(false)

// Registration can be closed on the server (REGISTRATION_OPEN=0). If the status
// did not load, the form stays: the server checks anyway.
const registrationOpen = ref(true)
// Protection from scripts (auth/registration.py on the server): the form token
// tells the server when the form was opened, the trap field stays empty for people.
const formToken = ref('')
const trap = ref('')

async function loadRegistration() {
  try {
    const status = await fetchRegistration()
    registrationOpen.value = status.open
    formToken.value = status.form_token
  } catch {
    // Without a token the server rejects the request, and the form loads it again.
  }
}

onMounted(loadRegistration)

async function submit() {
  clearErrors()
  // Password confirmation is checked only here, it is not sent to the server.
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
    userStore.setUser(await register({
      display_name, login, password, consents: consents.value,
      form_token: formToken.value, website: trap.value,
    }))
    emit('success')
  } catch (error) {
    if (error instanceof ApiError && error.code === 'registration_closed') {
      registrationOpen.value = false
    } else {
      showError(error)
      // A stale or missing token: a new one, so that the next attempt goes through.
      if (error instanceof ApiError && error.code === 'registration_rejected') {
        await loadRegistration()
      }
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
      hint="Минимум 8 символов, не совпадает с логином"
      :error="fieldErrors.password"
    />
    <AppInput
      v-model="form.password_repeat"
      label="Повторите пароль"
      type="password"
      autocomplete="new-password"
      :error="fieldErrors.password_repeat"
    />
    <!-- A trap for scripts: hidden from people and screen readers, filled only by bots. -->
    <div class="auth-form__trap" aria-hidden="true">
      <label>
        Сайт
        <input v-model="trap" type="text" name="website" tabindex="-1" autocomplete="off" />
      </label>
    </div>
    <ConsentFields v-model="consents" :errors="fieldErrors" />
    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" class="auth-form__submit" :loading="loading">Создать аккаунт</AppButton>
  </form>
</template>

<style scoped src="./authForm.css"></style>

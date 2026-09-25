<script setup lang="ts">
import { ref } from 'vue'
import { useFormErrors } from '@/shared/lib'
import { AppButton, AppInput } from '@/shared/ui'
import type { AddedParticipant } from '../api/participantsApi'

// Новый аккаунт с временным паролем: для встречи и для списка участников клуба.
// Куда добавить человека, решает переданная функция create.
const { create, submitLabel } = defineProps<{
  create: (displayName: string, login: string) => Promise<AddedParticipant>
  submitLabel: string
}>()
const emit = defineEmits<{ created: [result: AddedParticipant] }>()

const displayName = ref('')
const login = ref('')
const creating = ref(false)
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()

async function submit() {
  creating.value = true
  clearErrors()
  try {
    emit('created', await create(displayName.value, login.value))
  } catch (e) {
    showError(e)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <form class="newcomer-form" @submit.prevent="submit">
    <AppInput
      v-model="displayName"
      label="Имя и фамилия"
      autocomplete="off"
      :error="fieldErrors.display_name"
    />
    <AppInput
      v-model="login"
      label="Логин"
      autocomplete="off"
      hint="Латинские буквы и цифры"
      :error="fieldErrors.login"
    />
    <p v-if="formError" class="newcomer-form__error" role="alert">{{ formError }}</p>
    <AppButton type="submit" :loading="creating">{{ submitLabel }}</AppButton>
  </form>
</template>

<style scoped>
.newcomer-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.newcomer-form__error {
  color: var(--color-danger);
}
</style>

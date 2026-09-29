<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/entities/user'
import { AppButton, FormError } from '@/shared/ui'
import { acceptConsents } from '../api/authApi'
import { emptyConsents, missingConsents } from '../model/consents'
import { useFormErrors } from '@/shared/lib'
import ConsentFields from './ConsentFields.vue'

// Consents from someone who has none: the account was created by an organizer
// or the consent text was updated.
const emit = defineEmits<{ success: [] }>()

const userStore = useUserStore()
const { fieldErrors, formError, clearErrors, showError } = useFormErrors()
const consents = ref(emptyConsents())
const loading = ref(false)

async function submit() {
  clearErrors()
  const errors = missingConsents(consents.value)
  if (Object.keys(errors).length > 0) {
    fieldErrors.value = errors
    return
  }

  loading.value = true
  try {
    userStore.setUser(await acceptConsents(consents.value))
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
    <ConsentFields v-model="consents" :errors="fieldErrors" />
    <FormError v-if="formError" :message="formError" />
    <AppButton type="submit" class="auth-form__submit" :loading="loading">Продолжить</AppButton>
  </form>
</template>

<style scoped src="./authForm.css"></style>

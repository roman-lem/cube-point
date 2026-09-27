<script setup lang="ts">
import { ref } from 'vue'
import type { OrganizerPledge } from '@/entities/club'
import { ApiError } from '@/shared/api'
import { ConfirmDialog, FormError } from '@/shared/ui'
import { acceptPledge } from '../api/pledgeApi'

// Organizer pledge: until it is accepted, the organizer tools of the club stay closed
// (the server checks the same). The text comes from the server (backend/app/pledge.py).
// Closed with "Later", the dialog shows up again on the next visit to the page.
const { clubId, pledge } = defineProps<{ clubId: number; pledge: OrganizerPledge }>()

const emit = defineEmits<{ accepted: [] }>()

const open = ref(true)
const loading = ref(false)
const error = ref('')

async function accept() {
  loading.value = true
  error.value = ''
  try {
    await acceptPledge(clubId, pledge.version)
    open.value = false
    emit('accepted')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось сохранить'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <ConfirmDialog
    v-model:open="open"
    title="Обязательство организатора"
    confirm-label="Принимаю"
    cancel-label="Позже"
    :loading="loading"
    @confirm="accept"
  >
    <p>{{ pledge.text }}</p>
    <FormError v-if="error" :message="error" />
  </ConfirmDialog>
</template>

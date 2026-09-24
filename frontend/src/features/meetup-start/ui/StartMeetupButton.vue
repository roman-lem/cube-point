<script setup lang="ts">
import { ref } from 'vue'
import type { Meetup } from '@/entities/meetup'
import { ApiError, http } from '@/shared/api'
import { AppButton, AppIcon, ConfirmDialog } from '@/shared/ui'

const { meetupId } = defineProps<{ meetupId: number }>()
const emit = defineEmits<{ started: [meetup: Meetup] }>()

const confirmOpen = ref(false)
const loading = ref(false)
const error = ref('')

async function start() {
  loading.value = true
  error.value = ''
  try {
    const { meetup } = await http.post<{ meetup: Meetup }>(`/api/meetups/${meetupId}/start`)
    confirmOpen.value = false
    emit('started', meetup)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось запустить встречу'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppButton class="start-meetup" @click="confirmOpen = true">
    <AppIcon name="play" :size="20" />
    Запустить встречу
  </AppButton>
  <ConfirmDialog
    v-model:open="confirmOpen"
    title="Запустить встречу?"
    confirm-label="Запустить"
    :loading="loading"
    @confirm="start"
  >
    <p>Подтверждённые участники смогут начинать серии.</p>
    <p v-if="error" class="start-meetup__error">{{ error }}</p>
  </ConfirmDialog>
</template>

<style scoped>
.start-meetup {
  width: 100%;
}

.start-meetup__error {
  margin-top: var(--space-2);
  color: var(--color-danger);
}
</style>

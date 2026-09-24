<script setup lang="ts">
import { ref } from 'vue'
import type { MySeries } from '@/entities/series'
import { ApiError } from '@/shared/api'
import { eventName, type SeriesFormat } from '@/shared/lib'
import { AppButton, AppIcon, ConfirmDialog } from '@/shared/ui'
import { startSeries } from '../api/startSeries'

const { meetupId, eventId } = defineProps<{
  meetupId: number
  eventId: string
  format: SeriesFormat
}>()
const emit = defineEmits<{ started: [series: MySeries] }>()

const confirmOpen = ref(false)
const loading = ref(false)
const error = ref('')

async function start() {
  loading.value = true
  error.value = ''
  try {
    const series = await startSeries(meetupId, eventId)
    confirmOpen.value = false
    emit('started', series)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось начать серию'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AppButton class="start-series" @click="confirmOpen = true">
    <AppIcon name="play" :size="20" />
    Начать серию ({{ format }})
  </AppButton>
  <ConfirmDialog
    v-model:open="confirmOpen"
    :title="`Начать серию ${eventName(eventId)}?`"
    confirm-label="Начать"
    :loading="loading"
    @confirm="start"
  >
    <p>
      Результаты попадут в таблицу встречи. Попытки сдаются по порядку,
      сохранённую попытку изменить нельзя.
    </p>
    <p v-if="error" class="start-series__error">{{ error }}</p>
  </ConfirmDialog>
</template>

<style scoped>
.start-series {
  width: 100%;
}

.start-series__error {
  margin-top: var(--space-2);
  color: var(--color-danger);
}
</style>

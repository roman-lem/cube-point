<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ApiError } from '@/shared/api'
import { formatAttempt, formatDateTime, type Attempt, type ResultType } from '@/shared/lib'
import { ConfirmDialog } from '@/shared/ui'
import { fetchAttemptHistory, type AttemptHistoryEntry } from '../api/saveAttempt'
import { sameAttempt } from '../model/attemptText'
import type { AttemptSaving } from '../model/useAttemptSaving'

// History of a corrected attempt for the organizer: values in order, who set them
// and when. "Restore the original result" is a regular edit through the series queue.
const open = defineModel<boolean>('open', { required: true })
const { saving, eventId, user, number, attempt, resultType, timeZone } = defineProps<{
  saving: AttemptSaving
  eventId: string
  user: { id: number; display_name: string }
  number: number
  /** Current value of the attempt. */
  attempt: Attempt | null
  resultType: ResultType
  timeZone: string
}>()

const history = ref<AttemptHistoryEntry[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    history.value = await fetchAttemptHistory(saving.meetupId(), eventId, user.id, number)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить историю'
  } finally {
    loading.value = false
  }
}

watch(open, (value) => {
  if (value) {
    history.value = []
    load()
  }
}, { immediate: true })

const original = computed(() => history.value[0] ?? null)
const isOriginal = computed(() => !original.value || sameAttempt(original.value, attempt))

function restore() {
  open.value = false
  void saving.restore(eventId, user, number)
}
</script>

<template>
  <ConfirmDialog
    v-model:open="open"
    :title="`${user.display_name}, попытка ${number}`"
    confirm-label="Вернуть исходный результат"
    cancel-label="Закрыть"
    :confirm-disabled="loading || isOriginal"
    wide
    @confirm="restore"
  >
    <p v-if="loading">Загрузка…</p>
    <p v-else-if="error" class="attempt-history__error">{{ error }}</p>
    <ol v-else class="attempt-history">
      <li v-for="(entry, i) in history" :key="i" class="attempt-history__entry">
        <span class="attempt-history__value">{{ formatAttempt(entry, resultType) }}</span>
        <span>
          {{ i === 0 ? 'Исходный' : 'Исправлено' }} ·
          {{ entry.changed_by?.display_name ?? 'удалённый аккаунт' }} ·
          {{ formatDateTime(entry.changed_at, timeZone) }}
        </span>
        <span v-if="entry.solution" class="attempt-history__solution">{{ entry.solution }}</span>
      </li>
    </ol>
    <p v-if="!loading && !error && isOriginal">Сейчас у попытки исходный результат.</p>
  </ConfirmDialog>
</template>

<style scoped>
.attempt-history {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: 0;
  list-style: none;
}

.attempt-history__entry {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-1) var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.attempt-history__entry:last-child {
  border-bottom: none;
}

.attempt-history__value {
  min-width: 96px;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: var(--font-weight-label);
}

.attempt-history__solution {
  flex-basis: 100%;
  font-family: var(--font-mono);
  font-size: var(--font-size-label);
  overflow-wrap: anywhere;
}

.attempt-history__error {
  color: var(--color-danger);
}
</style>

<script setup lang="ts">
import { useDocumentVisibility, useIntervalFn } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { TimeValue } from '@/entities/attempt'
import { useCurrentClubStore } from '@/entities/club'
import { RecordBadge } from '@/entities/record'
import {
  ATTEMPTS_COUNT,
  AttemptSeries,
  fetchEventResults,
  ResultRow,
  type EventResults,
  type ResultsRow,
} from '@/entities/series'
import { useUserStore } from '@/entities/user'
import { ApiError } from '@/shared/api'
import { EVENTS, eventName, formatDate, formatName, plural, type EventId } from '@/shared/lib'
import { AppCard, LiveIndicator, PageHeader } from '@/shared/ui'

const { meetupId, eventId } = defineProps<{ meetupId: number; eventId: string }>()

// While the meetup is live, the table refreshes itself.
const REFRESH_MS = 5_000

const clubStore = useCurrentClubStore()
const userStore = useUserStore()
const data = ref<EventResults | null>(null)
const error = ref('')
const expanded = ref(new Set<number>())

async function load() {
  try {
    data.value = await fetchEventResults(meetupId, eventId)
    error.value = ''
    clubStore.setClubId(data.value.meetup.club.id)
  } catch (e) {
    // A connection error during polling does not hide the table already shown.
    if (!data.value) {
      error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить результаты'
    }
  }
}

watch(() => [meetupId, eventId], () => {
  data.value = null
  expanded.value = new Set()
  load()
}, { immediate: true })

const isLive = computed(() => data.value?.meetup.status === 'live')
const visibility = useDocumentVisibility()

useIntervalFn(() => {
  if (isLive.value && visibility.value === 'visible') {
    load()
  }
}, REFRESH_MS)

const resultType = computed(() => EVENTS[eventId as EventId]?.resultType ?? 'time')
const format = computed(() => data.value?.event.format ?? 'ao5')
const isAverageFormat = computed(() => format.value === 'ao5' || format.value === 'mo3')

const subtitle = computed(() => {
  if (!data.value) return ''
  return [
    formatName(format.value),
    formatDate(data.value.meetup.date),
    plural(data.value.rows.length, ['участник', 'участника', 'участников']),
  ].join(' · ')
})

function isMe(row: ResultsRow) {
  return row.user.id === userStore.user?.id
}

function setExpanded(userId: number, value: boolean) {
  const next = new Set(expanded.value)
  if (value) {
    next.add(userId)
  } else {
    next.delete(userId)
  }
  expanded.value = next
}

function progress(row: ResultsRow) {
  if (row.status === 'completed') return undefined
  return {
    done: row.attempts.filter((a) => a !== null).length,
    total: ATTEMPTS_COUNT[format.value],
  }
}
</script>

<template>
  <main class="page">
    <PageHeader
      :title="eventName(eventId)"
      :subtitle="subtitle"
      :back-to="{ name: 'meetup', params: { meetupId } }"
    >
      <template v-if="isLive" #action>
        <LiveIndicator />
      </template>
    </PageHeader>

    <AppCard v-if="error">{{ error }}</AppCard>

    <template v-else-if="data">
      <AppCard v-if="data.rows.length === 0" class="page__muted">
        Результатов пока нет
      </AppCard>

      <section v-else class="event-results">
        <ResultRow
          v-for="row in data.rows"
          :key="row.user.id"
          :expanded="expanded.has(row.user.id)"
          :place="row.place"
          :name="row.user.display_name"
          :profile-to="row.user.has_profile
            ? { name: 'user-profile', params: { userId: row.user.id } }
            : undefined"
          :is-me="isMe(row)"
          :result-label="format"
          :progress="progress(row)"
          @update:expanded="setExpanded(row.user.id, $event)"
        >
          <template v-if="isAverageFormat" #single>
            <TimeValue :value="row.best" :result-type="resultType" />
            <RecordBadge v-for="mark in row.marks.single" :key="mark" :mark="mark" />
          </template>
          <template #result>
            <span class="event-results__result">
              <RecordBadge
                v-for="mark in isAverageFormat ? row.marks.average : row.marks.single"
                :key="mark"
                :mark="mark"
              />
              <TimeValue
                :value="isAverageFormat ? row.average : row.best"
                :result-type="resultType"
                :is-average="isAverageFormat"
                size="large"
              />
            </span>
          </template>
          <p class="event-results__attempts-title">
            {{ isAverageFormat ? 'Попытки (отброшенные в скобках)' : 'Попытки' }}
          </p>
          <AttemptSeries :attempts="row.attempts" :format="format" :result-type="resultType" />
        </ResultRow>
      </section>
    </template>
  </main>
</template>

<style scoped>
.event-results {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.event-results__result {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.event-results__attempts-title {
  margin-bottom: var(--space-2);
  color: var(--color-text-secondary);
  font-size: 12px;
}
</style>

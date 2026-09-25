<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TimeValue } from '@/entities/attempt'
import {
  fetchDesk, fetchMeetup, type DeskEvent, type MeetupDesk, type MeetupPageData,
} from '@/entities/meetup'
import { AttemptField, AttemptHistoryDialog, useAttemptSaving } from '@/features/attempt-edit'
import { DisqualificationControl } from '@/features/disqualification'
import { ApiError } from '@/shared/api'
import { ATTEMPTS_COUNT, EVENTS, FORMAT_NAMES, eventName, type EventId } from '@/shared/lib'
import { AppCard, PageHeader } from '@/shared/ui'

// Ручной ввод и правка результатов участника организатором (макет org_series_edit).
// Кнопок «Сохранить» нет: каждое поле сохраняется само.
const { meetupId, userId } = defineProps<{ meetupId: number; userId: number }>()

const page = ref<MeetupPageData | null>(null)
const desk = ref<MeetupDesk | null>(null)
const error = ref('')
const tab = ref('')

async function load() {
  try {
    ;[page.value, desk.value] = await Promise.all([fetchMeetup(meetupId), fetchDesk(meetupId)])
    if (!desk.value.events.some((e) => e.event_id === tab.value)) {
      tab.value = desk.value.events[0]?.event_id ?? ''
    }
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить данные'
  }
}

watch(() => [meetupId, userId], load, { immediate: true })

const participant = computed(() => desk.value?.participants.find((p) => p.user.id === userId))
const event = computed(() => desk.value?.events.find((e) => e.event_id === tab.value))
const row = computed(() => event.value?.rows.find((r) => r.user.id === userId))
const resultType = computed(() => EVENTS[tab.value as EventId]?.resultType ?? 'time')
const numbers = computed(() =>
  event.value ? Array.from({ length: ATTEMPTS_COUNT[event.value.format] }, (_, i) => i + 1) : [],
)
const done = computed(() => row.value?.series?.attempts.filter(Boolean).length ?? 0)
const hasAverage = computed(() => event.value?.format === 'ao5' || event.value?.format === 'mo3')

const seriesStatus = computed(() => {
  const series = row.value?.series
  if (!series) {
    return 'Серия не начата'
  }
  return series.status === 'completed' ? 'Серия завершена' : 'Серия в процессе'
})

function replaceEvent(fresh: DeskEvent) {
  if (desk.value) {
    desk.value = {
      ...desk.value,
      events: desk.value.events.map((e) => (e.event_id === fresh.event_id ? fresh : e)),
    }
  }
}

const saving = useAttemptSaving({
  meetupId: () => meetupId,
  version: (eventId, id) =>
    desk.value?.events.find((e) => e.event_id === eventId)?.rows.find((r) => r.user.id === id)
      ?.series?.version ?? null,
  onEvent: replaceEvent,
})

/** Номер попытки, история которой открыта. */
const historyNumber = ref<number | null>(null)
const historyOpen = ref(false)

function showHistory(number: number) {
  historyNumber.value = number
  historyOpen.value = true
}
</script>

<template>
  <main class="page page--narrow">
    <PageHeader
      :title="participant?.user.display_name ?? 'Ввод результатов'"
      subtitle="Ввод результатов"
      :back-to="{ name: 'meetup-manage', params: { meetupId } }"
    />
    <AppCard v-if="error">{{ error }}</AppCard>
    <AppCard v-else-if="page && page.my_role !== 'organizer'">
      Ввод результатов доступен только организатору клуба
    </AppCard>
    <AppCard v-else-if="desk && !participant">Участник не подтверждён на этой встрече</AppCard>
    <AppCard v-else-if="page?.meetup.status === 'planned'">
      Встреча ещё не началась — результаты можно вводить после запуска
    </AppCard>

    <template v-else-if="desk && participant && page">
      <AppCard class="series-edit__person">
        <div>
          <p class="series-edit__login">{{ participant.user.login }}</p>
          <p v-if="participant.disqualification" class="series-edit__reason">
            Причина дисквалификации: {{ participant.disqualification.reason }}
          </p>
        </div>
        <DisqualificationControl
          :meetup-id="meetupId"
          :user="participant.user"
          :disqualification="participant.disqualification"
          @changed="load"
        />
      </AppCard>

      <div class="series-edit__tabs" role="tablist">
        <button
          v-for="e in desk.events"
          :key="e.event_id"
          type="button"
          role="tab"
          :aria-selected="tab === e.event_id"
          :class="['series-edit__tab', { 'series-edit__tab--active': tab === e.event_id }]"
          @click="tab = e.event_id"
        >
          {{ eventName(e.event_id) }}
        </button>
      </div>

      <section v-if="event" :key="event.event_id" class="page__section">
        <div class="series-edit__event">
          <h2 class="page__section-title">
            {{ eventName(event.event_id) }} · {{ FORMAT_NAMES[event.format] }}
          </h2>
          <span class="page__muted">{{ seriesStatus }}</span>
        </div>

        <AttemptField
          v-for="number in numbers"
          :key="number"
          :number="number"
          :attempt="row?.series?.attempts[number - 1] ?? null"
          :result-type="resultType"
          :disabled="number > done + 1"
          :state="saving.stateOf(event.event_id, userId, number)"
          :solution="row?.series?.attempts[number - 1]?.solution"
          :edited="row?.series?.attempts[number - 1]?.edited"
          @save="saving.save(event.event_id, participant.user, number, $event)"
          @history="showHistory(number)"
        />
        <AttemptHistoryDialog
          v-if="historyNumber"
          v-model:open="historyOpen"
          :saving="saving"
          :event-id="event.event_id"
          :user="participant.user"
          :number="historyNumber"
          :attempt="row?.series?.attempts[historyNumber - 1] ?? null"
          :result-type="resultType"
          :time-zone="page.meetup.club.timezone"
        />

        <AppCard class="series-edit__summary">
          <div>
            <p class="page__muted">Лучшая</p>
            <TimeValue :value="row?.series?.best ?? null" :result-type="resultType" size="large" />
          </div>
          <div v-if="hasAverage">
            <p class="page__muted">Среднее ({{ event.format }})</p>
            <TimeValue
              :value="row?.series?.average ?? null"
              :result-type="resultType"
              is-average
              size="large"
            />
          </div>
          <div v-if="row?.place">
            <p class="page__muted">Место</p>
            <p class="series-edit__place">{{ row.place }}</p>
          </div>
        </AppCard>
        <p v-if="saving.notice.value" class="series-edit__notice" role="alert">
          {{ saving.notice.value }}
        </p>
        <p class="page__muted">Каждая попытка сохраняется сама — при выходе из поля или по Enter.</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.series-edit__person {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.series-edit__login {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.series-edit__reason {
  font-size: var(--font-size-label);
}

.series-edit__tabs {
  display: flex;
  gap: var(--space-1);
  overflow-x: auto;
  border-bottom: 1px solid var(--color-border);
}

.series-edit__tab {
  flex-shrink: 0;
  height: 40px;
  padding: 0 var(--space-4);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.series-edit__tab--active {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

.series-edit__event {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

.series-edit__summary {
  display: flex;
  gap: var(--space-5);
}

.series-edit__place {
  font-family: var(--font-mono);
  font-size: var(--font-size-time-large);
  font-weight: var(--font-weight-time-large);
}

.series-edit__notice {
  color: var(--color-danger);
}
</style>

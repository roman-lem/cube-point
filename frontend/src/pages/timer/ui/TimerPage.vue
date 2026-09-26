<script setup lang="ts">
import { useEventListener, useWakeLock } from '@vueuse/core'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchActiveMeetups, type ActiveMeetup } from '@/entities/meetup'
import { TimeValue } from '@/entities/attempt'
import { fetchMySeries, type MySeries } from '@/entities/series'
import {
  TrainingSolveActions,
  useTrainingSession,
  type TrainingSolve,
} from '@/entities/training-session'
import { submitAttempt } from '@/features/attempt-submit'
import { StartSeriesButton } from '@/features/series-start'
import { ApiError } from '@/shared/api'
import {
  ATTEMPTS_COUNT,
  EVENTS,
  TIMER_EVENT_IDS,
  formatAttempt,
  formatResult,
  randomScramble,
  type EventId,
} from '@/shared/lib'
import { AppButton, AppCard, AppSelect, ConfirmDialog } from '@/shared/ui'
import { TimerScreen, type TimerResult } from '@/widgets/timer'

// Timer. The mode is in the URL to survive a reload:
//   /timer?event=333                          — training (default);
//   /timer?event=333&meetup=5                 — training with "Start series" for meetup 5;
//   /timer?event=333&meetup=5&mode=series     — competition mode.
// Rules: "Timer" in docs/ARCHITECTURE.md. No FMC here yet. Training session
// statistics are on the "Statistics" tab.

const route = useRoute()
const router = useRouter()

const eventOptions = TIMER_EVENT_IDS.map((id) => ({ value: id, label: EVENTS[id].name }))

const eventId = computed<EventId>(() => {
  const value = route.query.event as EventId
  return TIMER_EVENT_IDS.includes(value) ? value : '333'
})
const meetupParam = computed(() => Number(route.query.meetup) || null)
const isSeriesMode = computed(() => route.query.mode === 'series')

function go(query: { event: string; meetup?: number | null; mode?: 'series' }) {
  router.replace({
    query: {
      event: query.event,
      ...(query.meetup ? { meetup: String(query.meetup) } : {}),
      ...(query.mode ? { mode: query.mode } : {}),
    },
  })
}

// Changing the event always leads to training.
const selectedEvent = computed({
  get: () => eventId.value,
  set: (value: EventId) => go({ event: value, meetup: meetupParam.value }),
})

// The meetup where the selected event can be solved

const activeMeetups = ref<ActiveMeetup[] | null>(null)

async function loadActive() {
  try {
    activeMeetups.value = await fetchActiveMeetups()
  } catch {
    activeMeetups.value = activeMeetups.value ?? []
  }
}

onMounted(loadActive)

const context = computed(() => {
  const candidates = (activeMeetups.value ?? []).filter((m) =>
    m.events.some((e) => e.event_id === eventId.value),
  )
  const meetup = candidates.find((m) => m.id === meetupParam.value) ?? candidates[0]
  if (!meetup) {
    return null
  }
  return { meetup, event: meetup.events.find((e) => e.event_id === eventId.value)! }
})

// Training

const trainingScramble = ref<string | null>(null)
let scrambleRequest = 0

async function nextScramble() {
  const request = ++scrambleRequest
  trainingScramble.value = null
  const scramble = await randomScramble(eventId.value)
  // The event may have changed while generating.
  if (request === scrambleRequest) {
    trainingScramble.value = scramble
  }
}

// A solve goes into the event's session right away, without confirmation.
const training = useTrainingSession(eventId)
const { last: lastSolve } = training

function onSolved(result: TimerResult) {
  if (result.value !== null) {
    training.add(result.value, result.penalty)
  }
  nextScramble()
}

// Deleting the last solve requires confirmation.
const removing = ref<TrainingSolve | null>(null)
const removeOpen = computed({
  get: () => removing.value !== null,
  set: (open: boolean) => {
    if (!open) removing.value = null
  },
})

function confirmRemove() {
  if (removing.value) {
    training.remove(removing.value.at)
  }
  removing.value = null
}

watch([eventId, isSeriesMode], () => {
  if (!isSeriesMode.value) {
    nextScramble()
  }
}, { immediate: true })

// Series

const timerScreen = ref<InstanceType<typeof TimerScreen>>()
const series = ref<MySeries | null>(null)
const seriesError = ref('')
const notice = ref('')
const saving = ref(false)
const pending = ref<TimerResult | null>(null)

// An unsaved attempt survives a page reload.
const pendingKey = computed(() =>
  series.value?.next_attempt ? `pending-attempt:${series.value.id}:${series.value.next_attempt.number}` : null,
)

function readPending(key: string): TimerResult | null {
  try {
    const saved = sessionStorage.getItem(key)
    return saved ? (JSON.parse(saved) as TimerResult) : null
  } catch {
    return null
  }
}

watch(pending, (value) => {
  try {
    if (!pendingKey.value) return
    if (value) {
      sessionStorage.setItem(pendingKey.value, JSON.stringify(value))
    } else {
      sessionStorage.removeItem(pendingKey.value)
    }
  } catch {
    // Storage is unavailable (private mode): the attempt just will not survive a reload.
  }
})

async function loadSeries() {
  series.value = null
  seriesError.value = ''
  notice.value = ''
  if (!isSeriesMode.value || activeMeetups.value === null) {
    return
  }
  if (!context.value) {
    // The meetup is over or the participant is not approved: back to training.
    go({ event: eventId.value })
    return
  }
  try {
    const loaded = await fetchMySeries(context.value.meetup.id, eventId.value)
    if (!loaded) {
      go({ event: eventId.value, meetup: context.value.meetup.id })
      return
    }
    series.value = loaded
    pending.value = pendingKey.value ? readPending(pendingKey.value) : null
  } catch (e) {
    seriesError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить серию'
  }
}

// Reload the series only when the series itself changes, not on every
// update of the meetup list (it is reloaded after an attempt is saved).
const seriesTarget = computed(() =>
  isSeriesMode.value && activeMeetups.value !== null
    ? `${eventId.value}:${context.value?.meetup.id ?? ''}`
    : null,
)
watch(seriesTarget, loadSeries, { immediate: true })

function onStarted(started: MySeries) {
  series.value = started
  loadActive()
  go({ event: eventId.value, meetup: started.meetup_id, mode: 'series' })
}

function continueSeries() {
  go({ event: eventId.value, meetup: context.value?.meetup.id, mode: 'series' })
}

function toTraining() {
  go({ event: eventId.value, meetup: context.value?.meetup.id })
}

async function save(result: TimerResult) {
  if (!series.value) return
  saving.value = true
  notice.value = ''
  try {
    const response = await submitAttempt(series.value, result)
    const oldKey = pendingKey.value
    series.value = response.series
    if (response.conflict) {
      // Keep the attempt: if it is still the next one, it can be saved again.
      notice.value = response.series.next_attempt
        ? 'Серию успели изменить, данные обновлены. Проверьте время и сохраните ещё раз.'
        : 'Серию успели изменить, и она уже завершена.'
      if (!response.series.next_attempt) {
        pending.value = null
      }
    } else {
      if (oldKey) {
        try {
          sessionStorage.removeItem(oldKey)
        } catch {
          // see above
        }
      }
      pending.value = null
      timerScreen.value?.reset()
    }
    loadActive()
  } catch (e) {
    notice.value = e instanceof ApiError ? e.message : 'Не удалось сохранить попытку'
  } finally {
    saving.value = false
  }
}

useEventListener(window, 'beforeunload', (event: BeforeUnloadEvent) => {
  if (pending.value) {
    event.preventDefault()
  }
})

// The screen stays on while a series is in progress.
const wakeLock = useWakeLock()
watch(
  () => isSeriesMode.value && series.value?.status === 'in_progress',
  async (active) => {
    try {
      if (active) {
        await wakeLock.request('screen')
      } else {
        await wakeLock.release()
      }
    } catch {
      // Not supported or not allowed: no big deal.
    }
  },
)

const attemptsCount = computed(() => (series.value ? ATTEMPTS_COUNT[series.value.format] : 0))

const seriesResult = computed(() => {
  const s = series.value
  if (!s) return ''
  return s.format === 'ao5' || s.format === 'mo3'
    ? formatResult(s.average, 'time', true)
    : formatResult(s.best, 'time')
})
</script>

<template>
  <main class="page timer-page">
    <!-- Competition mode -->
    <template v-if="isSeriesMode">
      <AppCard v-if="seriesError">{{ seriesError }}</AppCard>

      <AppCard v-else-if="series?.status === 'completed'" class="timer-page__done">
        <p class="timer-page__done-title">Серия завершена</p>
        <p :class="['timer-page__done-result', { 'timer-page__done-result--dnf': seriesResult === 'DNF' }]">
          {{ seriesResult }}
        </p>
        <p class="page__muted">{{ series.format }}</p>
        <RouterLink
          class="timer-page__link"
          :to="{ name: 'event-results', params: { meetupId: series.meetup_id, eventId: series.event_id } }"
        >
          Таблица результатов
        </RouterLink>
        <AppButton variant="secondary" @click="toTraining">К тренировке</AppButton>
      </AppCard>

      <TimerScreen
        v-else-if="series?.next_attempt"
        ref="timerScreen"
        v-model:pending="pending"
        mode="series"
        :event-id="series.event_id"
        :scramble="series.next_attempt.scramble"
        :scramble-title="`Серия · попытка ${series.next_attempt.number} из ${attemptsCount}`"
        :saving="saving"
        @save="save"
      >
        <template #header>
          <div class="timer-page__header">
            <AppSelect v-model="selectedEvent" :options="eventOptions" aria-label="Дисциплина" />
            <AppButton variant="secondary" @click="toTraining">К тренировке</AppButton>
          </div>
        </template>
        <template #actions>
          <p v-if="notice" class="timer-page__notice" role="alert">{{ notice }}</p>
        </template>
      </TimerScreen>

      <AppCard v-else class="page__muted">Загружаем серию…</AppCard>
    </template>

    <!-- Training -->
    <TimerScreen
      v-else
      mode="training"
      :event-id="eventId"
      :scramble="trainingScramble"
      scramble-title="Тренировка"
      can-refresh
      :last="lastSolve"
      @solved="onSolved"
      @refresh-scramble="nextScramble"
    >
      <template #header>
        <div class="timer-page__header">
          <AppSelect v-model="selectedEvent" :options="eventOptions" aria-label="Дисциплина" />
        </div>
      </template>
      <template v-if="context" #actions>
        <StartSeriesButton
          v-if="!context.event.series"
          :meetup-id="context.meetup.id"
          :event-id="eventId"
          :format="context.event.format"
          @started="onStarted"
        />
        <AppButton v-else-if="context.event.series.status === 'in_progress'" @click="continueSeries">
          Продолжить серию ({{ context.event.series.attempts_done }} из
          {{ ATTEMPTS_COUNT[context.event.format] }})
        </AppButton>
        <RouterLink
          v-else
          class="timer-page__link"
          :to="{ name: 'event-results', params: { meetupId: context.meetup.id, eventId } }"
        >
          Серия сдана — таблица результатов
        </RouterLink>
      </template>
      <template v-if="lastSolve" #last>
        <div class="timer-page__last">
          <span class="page__muted">Последняя:</span>
          <TimeValue :value="lastSolve.value" :penalty="lastSolve.penalty" size="large" />
          <TrainingSolveActions
            :penalty="lastSolve.penalty"
            @penalty="(penalty) => training.setPenalty(lastSolve!.at, penalty)"
            @remove="removing = lastSolve"
          />
        </div>
      </template>
    </TimerScreen>

    <ConfirmDialog
      v-model:open="removeOpen"
      :title="`Удалить сборку ${removing ? formatAttempt(removing, 'time') : ''}?`"
      confirm-label="Удалить"
      danger
      @confirm="confirmRemove"
    >
      Сборка удалится из тренировочной сессии.
    </ConfirmDialog>
  </main>
</template>

<style scoped>
.timer-page {
  flex: 1;
  gap: var(--space-3);
}

.timer-page__header {
  display: flex;
  gap: var(--space-2);
}

.timer-page__header > :first-child {
  flex: 1;
}

.timer-page__last {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: var(--space-2) var(--space-3);
}

.timer-page__notice {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.timer-page__done {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  text-align: center;
}

.timer-page__done-title {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.timer-page__done-result {
  font-family: var(--font-mono);
  font-size: 40px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.timer-page__done-result--dnf {
  color: var(--color-dnf);
}

.timer-page__link {
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
  text-align: center;
}
</style>

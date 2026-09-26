<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { TimeValue } from '@/entities/attempt'
import { AttemptSeries, fetchLiveSeries, type LiveSeries, type LiveSeriesMeetup } from '@/entities/series'
import {
  TrainingSolveList,
  TrainingStats,
  useTrainingSession,
  type TrainingSolve,
} from '@/entities/training-session'
import { ApiError } from '@/shared/api'
import {
  ATTEMPTS_COUNT,
  EVENTS,
  TIMER_EVENT_IDS,
  eventName,
  formatAttempt,
  formatDate,
  plural,
  type EventId,
} from '@/shared/lib'
import { AppButton, AppCard, AppIcon, AppSelect, ConfirmDialog, PageHeader } from '@/shared/ui'

// Statistics: one's own series at live meetups
// and the training session of the selected event. The event is in the URL
// (/statistics?event=222) to survive a reload.

const route = useRoute()
const router = useRouter()

// Series at meetups

const meetups = ref<LiveSeriesMeetup[]>([])
const seriesError = ref('')

onMounted(async () => {
  try {
    meetups.value = await fetchLiveSeries()
  } catch (e) {
    seriesError.value = e instanceof ApiError ? e.message : 'Не удалось загрузить серии'
  }
})

function attemptsDone(series: LiveSeries) {
  return series.attempts.filter((a) => a !== null).length
}

function attemptsLeft(series: LiveSeries) {
  return ATTEMPTS_COUNT[series.format] - attemptsDone(series)
}

const isAverageFormat = (series: LiveSeries) => series.format === 'ao5' || series.format === 'mo3'
const isFmc = (series: LiveSeries) => EVENTS[series.event_id as EventId]?.resultType === 'moves'
const resultType = (series: LiveSeries) => (isFmc(series) ? 'moves' : 'time')

// "Continue" opens competition mode right away, without confirmation.
// FMC has its own screen.
function continueRoute(meetupId: number, series: LiveSeries) {
  if (isFmc(series)) {
    return { name: 'fmc', params: { meetupId } }
  }
  return {
    name: 'timer',
    query: { event: series.event_id, meetup: String(meetupId), mode: 'series' },
  }
}

// Training session

const eventOptions = TIMER_EVENT_IDS.map((id) => ({ value: id, label: EVENTS[id].name }))

const eventId = computed<EventId>({
  get: () => {
    const value = route.query.event as EventId
    return TIMER_EVENT_IDS.includes(value) ? value : '333'
  },
  set: (value) => router.replace({ query: { event: value } }),
})

const training = useTrainingSession(eventId)
const { solves, stats } = training

const removing = ref<{ solve: TrainingSolve; number: number } | null>(null)
const removeOpen = computed({
  get: () => removing.value !== null,
  set: (open: boolean) => {
    if (!open) removing.value = null
  },
})

function confirmRemove() {
  if (removing.value) {
    training.remove(removing.value.solve.at)
  }
  removing.value = null
}

const clearOpen = ref(false)

function confirmClear() {
  training.clear()
  clearOpen.value = false
}
</script>

<template>
  <main class="page statistics">
    <PageHeader title="Статистика" />

    <AppCard v-if="seriesError" class="page__muted">{{ seriesError }}</AppCard>

    <!-- Series at live meetups -->
    <section v-for="meetup in meetups" :key="meetup.id" class="page__section">
      <div>
        <h2 class="page__section-title">{{ meetup.club.name }}</h2>
        <p class="page__muted">Встреча {{ formatDate(meetup.date) }}</p>
      </div>

      <AppCard v-for="series in meetup.series" :key="series.id" class="statistics__series">
        <div class="statistics__series-head">
          <span class="statistics__series-title">
            Серия {{ eventName(series.event_id) }} ·
            {{ series.status === 'in_progress' ? 'в процессе' : 'завершена' }}
          </span>
          <span class="statistics__series-progress">
            {{ attemptsDone(series) }} / {{ ATTEMPTS_COUNT[series.format] }}
          </span>
        </div>

        <AttemptSeries
          :attempts="series.attempts"
          :format="series.format"
          :result-type="resultType(series)"
        />

        <div v-if="series.status === 'in_progress'" class="statistics__series-foot">
          <span class="page__muted">
            Осталось {{ plural(attemptsLeft(series), ['попытка', 'попытки', 'попыток']) }}
          </span>
          <RouterLink :to="continueRoute(meetup.id, series)" class="statistics__continue">
            Продолжить
            <AppIcon name="chevron-right" :size="20" />
          </RouterLink>
        </div>

        <div v-else class="statistics__series-foot">
          <span class="statistics__result">
            <span class="page__muted">{{ isAverageFormat(series) ? 'Среднее' : 'Лучшая' }}</span>
            <TimeValue
              :value="isAverageFormat(series) ? series.average : series.best"
              :is-average="isAverageFormat(series)"
              :result-type="resultType(series)"
              size="large"
            />
          </span>
          <RouterLink
            class="statistics__link"
            :to="{ name: 'event-results', params: { meetupId: meetup.id, eventId: series.event_id } }"
          >
            Таблица результатов
          </RouterLink>
        </div>
      </AppCard>
    </section>

    <!-- Training session -->
    <section class="page__section">
      <div class="statistics__training-head">
        <h2 class="page__section-title">Тренировка</h2>
        <AppSelect v-model="eventId" :options="eventOptions" aria-label="Дисциплина" />
      </div>

      <AppCard class="statistics__training">
        <TrainingStats :stats="stats" />

        <TrainingSolveList
          v-if="solves.length > 0"
          :solves="solves"
          @penalty="training.setPenalty"
          @remove="(solve, number) => (removing = { solve, number })"
        />
        <p v-else class="page__muted statistics__empty">
          Сборок пока нет.
          <RouterLink class="statistics__link" :to="{ name: 'timer', query: { event: eventId } }">
            Открыть таймер
          </RouterLink>
        </p>

        <AppButton v-if="solves.length > 0" variant="secondary" @click="clearOpen = true">
          Новая сессия
        </AppButton>
      </AppCard>
    </section>

    <ConfirmDialog
      v-model:open="removeOpen"
      :title="`Удалить сборку #${removing?.number}?`"
      confirm-label="Удалить"
      danger
      @confirm="confirmRemove"
    >
      {{ removing ? formatAttempt(removing.solve, 'time') : '' }} — сборка удалится из
      тренировочной сессии.
    </ConfirmDialog>

    <ConfirmDialog
      v-model:open="clearOpen"
      :title="`Начать новую сессию ${eventName(eventId)}?`"
      confirm-label="Начать заново"
      danger
      @confirm="confirmClear"
    >
      Все {{ plural(solves.length, ['сборка', 'сборки', 'сборок']) }} текущей сессии будут удалены.
    </ConfirmDialog>
  </main>
</template>

<style scoped>
.statistics__series {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.statistics__series-head,
.statistics__series-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.statistics__series-title {
  font-weight: var(--font-weight-label);
}

.statistics__series-progress {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--font-size-time-small);
  font-variant-numeric: tabular-nums;
}

.statistics__continue {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: var(--control-height);
  padding: 0 var(--space-4);
  background: var(--color-primary);
  border-radius: var(--radius-button);
  color: var(--color-on-primary);
  font-weight: var(--font-weight-label);
}

.statistics__result {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-2);
}

.statistics__link {
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
}

.statistics__training-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.statistics__training {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.statistics__empty {
  text-align: center;
}
</style>

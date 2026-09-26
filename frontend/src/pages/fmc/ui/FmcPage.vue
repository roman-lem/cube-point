<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TimeValue } from '@/entities/attempt'
import { fetchMeetup, type MeetupPageData } from '@/entities/meetup'
import { AttemptSeries, fetchMySeries, type MySeries } from '@/entities/series'
import {
  FmcSubmitDialog,
  formatCountdown,
  freezeFmcSolution,
  startFmcAttempt,
  submitFmcResult,
  unfreezeFmcSolution,
  useDraftAutosave,
  useFmcClock,
} from '@/features/fmc-solution'
import { startSeries } from '@/features/series-start'
import { ApiError } from '@/shared/api'
import {
  ATTEMPTS_COUNT,
  FMC_DNF_REASONS,
  checkSolution,
  formatDate,
  parseSolution,
  preloadSolutionCheck,
} from '@/shared/lib'
import { AppButton, AppCard, AppIcon, ConfirmDialog, PageHeader } from '@/shared/ui'
import { FmcKeyboard } from '@/widgets/fmc-keyboard'

// An FMC series at a meetup.
// Screen states: before the attempt starts → solving → frozen (submit dialog)
// → check and result. If time ran out without submission, the last saved
// draft is checked and sent automatically. Rules: "FMC" in docs/ARCHITECTURE.md.

const EVENT_ID = '333fm'
// The countdown turns red for the last 5 minutes.
const WARNING_MS = 5 * 60 * 1000
// Before the deadline an unsaved draft is sent immediately, without a delay.
const LAST_SAVE_MS = 1500

const { meetupId } = defineProps<{ meetupId: number }>()

const meetupData = ref<MeetupPageData | null>(null)
const series = ref<MySeries | null>(null)
const loaded = ref(false)
const error = ref('')

const meetupEvent = computed(
  () => meetupData.value?.meetup.events.find((e) => e.event_id === EVENT_ID) ?? null,
)
const format = computed(() => series.value?.format ?? meetupEvent.value?.format ?? 'bo1')
const attemptsCount = computed(() => ATTEMPTS_COUNT[format.value])
const attempt = computed(() => series.value?.next_attempt ?? null)
const fmcState = computed(() => attempt.value?.fmc ?? null)

async function load() {
  error.value = ''
  try {
    const [page, mine] = await Promise.all([
      fetchMeetup(meetupId),
      fetchMySeries(meetupId, EVENT_ID),
    ])
    meetupData.value = page
    setSeries(mine)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Не удалось загрузить серию'
  } finally {
    loaded.value = true
  }
}

// The solution is typed locally; the draft from the server comes on load and on a new state.
const moves = ref<string[]>([])
const solution = computed(() => moves.value.join(' '))

function setSeries(value: MySeries | null) {
  series.value = value
  const draft = value?.next_attempt?.fmc?.draft ?? ''
  moves.value = parseSolution(draft)
  autosave.reset(draft)
}

const { remaining } = useFmcClock(fmcState)
const timeOver = computed(() => remaining.value === 0)
const isFrozen = computed(() => Boolean(fmcState.value?.frozen_at))

type Stage = 'loading' | 'error' | 'start' | 'solving' | 'result'
const justSubmitted = ref(false)

const stage = computed<Stage>(() => {
  if (!loaded.value) return 'loading'
  if (error.value && !series.value && !meetupData.value) return 'error'
  if (justSubmitted.value || series.value?.status === 'completed') return 'result'
  if (fmcState.value) return 'solving'
  return 'start'
})

// cubing.js for the check is loaded in advance, during the attempt, so submission does not wait for the network.
watch(stage, (value) => {
  if (value === 'solving') preloadSolutionCheck()
}, { immediate: true })

const canSolve = computed(
  () =>
    meetupData.value?.meetup.status === 'live' &&
    meetupData.value.my_request?.status === 'approved' &&
    meetupEvent.value !== null,
)

// Draft

const autosaveEnabled = computed(
  () => stage.value === 'solving' && !isFrozen.value && !timeOver.value,
)
const autosave = useDraftAutosave(series, solution, autosaveEnabled)

watch(remaining, (ms) => {
  if (ms !== null && ms <= LAST_SAVE_MS && autosave.status.value === 'unsaved') {
    autosave.flush()
  }
})

const draftNote = computed(() => {
  switch (autosave.status.value) {
    case 'saving':
      return 'Сохраняем черновик…'
    case 'unsaved':
      return 'Черновик ещё не сохранён'
    default:
      return 'Черновик сохранён'
  }
})

// Attempt start

const startOpen = ref(false)
const starting = ref(false)
const startError = ref('')

async function start() {
  starting.value = true
  startError.value = ''
  try {
    const current = series.value ?? (await startSeries(meetupId, EVENT_ID))
    setSeries(await startFmcAttempt(current))
    startOpen.value = false
  } catch (e) {
    startError.value = e instanceof ApiError ? e.message : 'Не удалось начать попытку'
  } finally {
    starting.value = false
  }
}

// Submission: freeze → confirmation → check and saving the result

const submitOpen = ref(false)
const submitting = ref(false)
const submitError = ref('')
// Message on the result screen (e.g. freezing after the deadline).
const resultNote = ref('')

// Frozen (including in another tab): the submit dialog over the solving screen.
watch(isFrozen, (frozen) => {
  submitOpen.value = frozen
}, { immediate: true })

async function freeze() {
  if (!series.value) return
  submitting.value = true
  submitError.value = ''
  const attemptsBefore = series.value.attempts.length
  try {
    const updated = await freezeFmcSolution(series.value, solution.value)
    if (updated.attempts.length > attemptsBefore) {
      // Time ran out while the request was in flight: the server saved the solution as DNF.
      resultNote.value =
        'Время вышло до сдачи — решение сохранено как DNF. Если оно верное, обратитесь к организатору.'
      finishAttempt(updated)
    } else {
      series.value = updated
      submitOpen.value = true
    }
  } catch (e) {
    submitError.value = e instanceof ApiError ? e.message : 'Не удалось сдать решение'
  } finally {
    submitting.value = false
  }
}

async function backToSolving() {
  if (!series.value) return
  try {
    const updated = await unfreezeFmcSolution(series.value)
    series.value = updated
    autosave.reset(updated.next_attempt?.fmc?.draft ?? '')
  } catch (e) {
    submitError.value = e instanceof ApiError ? e.message : 'Не удалось вернуться к решению'
    submitOpen.value = true
    if (e instanceof ApiError && e.code === 'time_over') {
      await reloadSeries()
    }
  }
}

/** Checks the solution stored on the server and sends the result. */
async function checkAndSubmit(text: string) {
  const current = series.value
  if (!current?.next_attempt?.scramble) return
  submitting.value = true
  submitError.value = ''
  try {
    const check = await checkSolution(current.next_attempt.scramble, text)
    const response = await submitFmcResult(current, text, check)
    if (response.conflict) {
      setSeries(response.series)
      submitError.value = 'Решение успело измениться, проверьте его ещё раз'
    } else {
      if ('dnf' in check) {
        resultNote.value = [resultNote.value, FMC_DNF_REASONS[check.dnf]].filter(Boolean).join(' ')
      }
      finishAttempt(response.series)
    }
  } catch (e) {
    submitError.value = e instanceof ApiError ? e.message : 'Не удалось сохранить результат'
  } finally {
    submitting.value = false
  }
}

function confirmSubmit() {
  checkAndSubmit(fmcState.value?.frozen_solution ?? '')
}

// Time ran out without submission: the result is the last draft on the server.
let autoSubmitted = false

async function reloadSeries() {
  setSeries(await fetchMySeries(meetupId, EVENT_ID))
}

watch(
  () => stage.value === 'solving' && timeOver.value && !isFrozen.value,
  async (expired) => {
    if (!expired || autoSubmitted) return
    autoSubmitted = true
    await autosave.flush()
    try {
      await reloadSeries()
    } catch {
      autoSubmitted = false
      submitError.value = 'Нет связи с сервером. Решение проверится, когда связь появится.'
      return
    }
    if (fmcState.value && !fmcState.value.frozen_at) {
      resultNote.value = 'Время вышло — засчитан последний сохранённый черновик.'
      await checkAndSubmit(fmcState.value.draft)
    }
    autoSubmitted = false
  },
)

// Result

function finishAttempt(updated: MySeries) {
  series.value = updated
  submitOpen.value = false
  justSubmitted.value = true
  moves.value = []
  autosave.reset('')
  // The place in the table comes from the meetup page.
  fetchMeetup(meetupId).then((page) => (meetupData.value = page)).catch(() => {})
}

const lastAttempt = computed(() => series.value?.attempts.at(-1) ?? null)
const myPlace = computed(() => meetupEvent.value?.my_series ?? null)
const isAverageFormat = computed(() => format.value === 'mo3' || format.value === 'ao5')

function nextAttempt() {
  justSubmitted.value = false
  resultNote.value = ''
}

watch(() => meetupId, load, { immediate: true })

const title = computed(() => {
  const meetup = meetupData.value?.meetup
  return meetup ? `${meetup.club.name}, ${formatDate(meetup.date)}` : ''
})
const attemptTitle = computed(() =>
  attemptsCount.value > 1
    ? `Попытка ${attempt.value?.number ?? 1} из ${attemptsCount.value}`
    : 'Одна попытка (bo1)',
)
</script>

<template>
  <main class="page page--narrow fmc-page">
    <PageHeader
      title="FMC"
      :subtitle="title"
      :back-to="{ name: 'meetup', params: { meetupId } }"
    />

    <AppCard v-if="stage === 'loading'" class="page__muted">Загружаем серию…</AppCard>
    <AppCard v-else-if="stage === 'error'">{{ error }}</AppCard>

    <!-- Before the attempt starts -->
    <template v-else-if="stage === 'start'">
      <div class="fmc-page__locked">
        <AppIcon name="lock" :size="20" />
        Скрамбл появится после старта
      </div>

      <AppCard class="fmc-page__intro">
        <p class="fmc-page__limit"><span>60</span>мин</p>
        <h1 class="fmc-page__intro-title">Сборка на минимум ходов</h1>
        <p class="page__muted">
          У вас будет 60 минут, чтобы найти самое короткое решение. Отсчёт начнётся сразу
          после подтверждения старта.
        </p>
        <p class="fmc-page__format">{{ attemptTitle }}</p>
        <AttemptSeries
          v-if="series && series.attempts.length"
          :attempts="series.attempts"
          :format="format"
          result-type="moves"
        />
      </AppCard>

      <template v-if="canSolve">
        <AppButton @click="startOpen = true">Начать попытку</AppButton>
        <p class="fmc-page__hint">Для старта потребуется подтверждение</p>
      </template>
      <p v-else class="fmc-page__hint">
        Начать попытку можно во время встречи после подтверждения участия
      </p>

      <ConfirmDialog
        v-model:open="startOpen"
        title="Начать попытку FMC?"
        confirm-label="Начать"
        :loading="starting"
        @confirm="start"
      >
        <p>Сразу пойдёт отсчёт 60 минут и появится скрамбл. Остановить отсчёт нельзя.</p>
        <p v-if="startError" class="fmc-page__error">{{ startError }}</p>
      </ConfirmDialog>
    </template>

    <!-- Solving -->
    <template v-else-if="stage === 'solving' && fmcState && attempt">
      <AppCard class="fmc-page__clock">
        <span class="fmc-page__label">Осталось времени</span>
        <span
          :class="['fmc-page__countdown', {
            'fmc-page__countdown--warning': remaining !== null && remaining <= WARNING_MS,
          }]"
        >
          {{ formatCountdown(remaining ?? 0) }}
        </span>
        <span class="page__muted fmc-page__small">{{ attemptTitle }} · 60 минут на попытку</span>
      </AppCard>

      <AppCard class="fmc-page__block">
        <span class="fmc-page__label">Скрамбл</span>
        <p class="fmc-page__scramble">{{ attempt.scramble }}</p>
      </AppCard>

      <AppCard class="fmc-page__block">
        <span class="fmc-page__label">Ваше решение</span>
        <div class="fmc-page__solution" aria-live="polite">
          <span v-for="(move, index) in moves" :key="index" class="fmc-page__move">{{ move }}</span>
          <span v-if="!moves.length" class="page__muted">Наберите решение на клавиатуре</span>
        </div>
        <span class="page__muted fmc-page__small">{{ draftNote }}</span>
      </AppCard>

      <FmcKeyboard v-model="moves" :disabled="isFrozen || timeOver || submitting" />

      <AppButton :loading="submitting && !submitOpen" :disabled="isFrozen || timeOver" @click="freeze">
        Сдать решение
      </AppButton>
      <p v-if="submitError && !submitOpen" class="fmc-page__error" role="alert">{{ submitError }}</p>
      <p v-if="timeOver && !isFrozen" class="fmc-page__hint">Время вышло, проверяем решение…</p>

      <FmcSubmitDialog
        v-if="isFrozen"
        v-model:open="submitOpen"
        :state="fmcState"
        :time-over="timeOver"
        :loading="submitting"
        :error="submitError"
        @confirm="confirmSubmit"
        @back="backToSolving"
      />
    </template>

    <!-- Result -->
    <template v-else-if="stage === 'result' && series">
      <AppCard class="fmc-page__result">
        <span class="fmc-page__label">
          {{ series.status === 'completed' ? 'Серия завершена' : 'Попытка сдана' }}
        </span>
        <TimeValue
          v-if="lastAttempt"
          class="fmc-page__result-value"
          :value="lastAttempt.value"
          :penalty="lastAttempt.penalty"
          result-type="moves"
          size="large"
        />
        <span v-if="lastAttempt?.penalty === 'none'" class="page__muted">ходов</span>
        <p v-if="lastAttempt?.solution" class="fmc-page__scramble">{{ lastAttempt.solution }}</p>
        <p v-if="resultNote" class="page__muted">{{ resultNote }}</p>

        <template v-if="attemptsCount > 1">
          <AttemptSeries :attempts="series.attempts" :format="format" result-type="moves" />
          <p v-if="isAverageFormat && series.status === 'completed'">
            Среднее: <TimeValue :value="series.average" result-type="moves" is-average />
          </p>
        </template>

        <p v-if="series.status === 'completed' && myPlace?.place" class="fmc-page__place">
          {{ myPlace.place }} место из {{ myPlace.total }}
        </p>
        <p v-else-if="series.status === 'completed'" class="page__muted">Без места</p>
        <p v-else class="page__muted">Место появится после всех попыток</p>

        <RouterLink
          class="fmc-page__link"
          :to="{ name: 'event-results', params: { meetupId, eventId: EVENT_ID } }"
        >
          Таблица результатов
        </RouterLink>
      </AppCard>
      <AppButton v-if="series.status === 'in_progress'" @click="nextAttempt">
        Следующая попытка
      </AppButton>
    </template>
  </main>
</template>

<style scoped>
.fmc-page {
  gap: var(--space-3);
}

.fmc-page__locked {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-text-secondary);
}

.fmc-page__intro,
.fmc-page__result,
.fmc-page__clock {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  text-align: center;
}

.fmc-page__limit {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  margin: var(--space-2) 0;
  border: 4px solid var(--color-primary);
  border-radius: 50%;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  line-height: 1;
}

.fmc-page__limit span {
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 700;
}

.fmc-page__intro-title {
  font-size: var(--font-size-heading);
  font-weight: var(--font-weight-heading);
}

.fmc-page__format {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.fmc-page__hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}

.fmc-page__error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}

.fmc-page__label {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  text-transform: uppercase;
}

.fmc-page__small {
  font-size: 12px;
}

.fmc-page__countdown {
  font-family: var(--font-mono);
  font-size: 48px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.fmc-page__countdown--warning {
  color: var(--color-dnf);
}

.fmc-page__block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.fmc-page__scramble {
  margin: 0;
  padding: var(--space-3);
  background: var(--color-background);
  border-radius: var(--radius-button);
  font-family: var(--font-mono);
  font-size: var(--font-size-time-small);
  word-spacing: 0.3em;
  text-align: center;
}

.fmc-page__solution {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  min-height: 88px;
  padding: var(--space-3);
  background: var(--color-background);
  border-radius: var(--radius-button);
}

.fmc-page__move {
  font-family: var(--font-mono);
  font-size: var(--font-size-time-large);
  font-weight: var(--font-weight-time-large);
}

.fmc-page__result-value {
  font-size: 40px;
}

.fmc-page__place {
  font-size: 18px;
  font-weight: var(--font-weight-heading);
}

.fmc-page__link {
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
}
</style>

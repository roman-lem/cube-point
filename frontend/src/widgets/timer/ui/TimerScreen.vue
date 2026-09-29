<script setup lang="ts">
import { useEventListener, useLocalStorage, useMediaQuery, useResizeObserver } from '@vueuse/core'
import { computed, nextTick, ref, toRef, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import {
  formatAttempt,
  formatResult,
  parseTimeInput,
  scrambleLines,
  scramblePieces,
  useScreenWakeLock,
} from '@/shared/lib'
import { AppButton, AppIcon, ConfirmDialog } from '@/shared/ui'
import { isFocused, type SuggestedPenalty } from '../model/machine'
import { timerNow } from '../model/clock'
import { inspectionCountdown, useTimer, type StoppedSolve } from '../model/useTimer'

/** Solve result: time without the penalty and the penalty. DNF may have a time. */
export interface TimerResult {
  value: number | null
  penalty: SuggestedPenalty
}

// Timer screen: the scramble and controls on top,
// everything else is the touch area.
//
// training: a solve goes straight to solved and the page saves it to the session;
// last is the last solve of the session, the last slot is the "Last" line under the timer.
// series: after a solve the participant picks OK / +2 / DNF and presses
// "Save attempt" (save). The unsaved result is v-model:pending,
// so the page can keep it across a reload.
//
// The timer state is in the timer store (owner is whose solve it is), so it survives
// leaving the screen and a reload. During inspection and a solve only the timer
// is on the screen; leaving requires confirmation.
const pending = defineModel<TimerResult | null>('pending', { default: null })

const { mode, owner, eventId, scramble, saving = false, last = null } = defineProps<{
  mode: 'training' | 'series'
  /** Whose solve it is: `training:<event_id>` or `series:<series_id>:<attempt>`. */
  owner: string
  /** Megaminx scrambles are shown line by line. */
  eventId: string
  /** null: the scramble is still being generated or loaded. */
  scramble: string | null
  /** Scramble block title: «Тренировка», «Попытка 3 из 5». */
  scrambleTitle: string
  /** New scramble button (training only). */
  canRefresh?: boolean
  saving?: boolean
  /** The last training solve: shown on the display right after the solve. */
  last?: TimerResult | null
}>()

const emit = defineEmits<{
  solved: [result: TimerResult]
  save: [result: TimerResult]
  'refresh-scramble': []
}>()

// Timer settings are a convenience of this device, stored in the browser.
const inspection = useLocalStorage('timer-inspection', false)
const manual = useLocalStorage('timer-manual', false)
const isTouch = useMediaQuery('(pointer: coarse)')

// Expanded long scramble: the timer zone is gone, so that a touch does not start a solve by mistake.
const expanded = ref(false)

const enabled = computed(
  () => !manual.value && !expanded.value && scramble !== null && !saving && pending.value === null,
)

// Leave confirmation: the navigation waits for the answer.
const leaveOpen = ref(false)

const timer = useTimer({
  owner: toRef(() => owner),
  inspection: toRef(inspection),
  enabled,
  blocked: leaveOpen,
  onStop: finish,
})
const { state, elapsed, inspectionElapsed, onZonePointerDown } = timer

function finish(solve: StoppedSolve) {
  const result: TimerResult = { value: solve.value, penalty: solve.penalty }
  if (mode === 'series') {
    pending.value = result
  } else {
    emit('solved', result)
  }
}

// Long scrambles (big cubes, megaminx) get a smaller font, and the block
// has a height limit with scrolling, so that the touch area stays large.
// If the scramble does not fit, it can be expanded to be read whole.
// Each line is split into pieces that are not broken (Square-1 wraps only after "/").
const lines = computed(() =>
  scramble === null
    ? null
    : scrambleLines(eventId, scramble).map((line) => scramblePieces(eventId, line)),
)
const scrambleSize = computed(() => {
  if (eventId === 'minx') return 'lines'
  const length = scramble?.length ?? 0
  return length > 200 ? 'small' : length > 80 ? 'medium' : 'large'
})

const scrambleText = ref<HTMLElement>()
/** The collapsed scramble does not fit its block: it can be expanded. */
const overflows = ref(false)

function measure() {
  const element = scrambleText.value
  // The expanded block has no height limit: keep what was measured when collapsed.
  if (element && !expanded.value) {
    overflows.value = element.scrollHeight > element.clientHeight + 1
  }
}

useResizeObserver(scrambleText, measure)
// A new scramble starts collapsed.
watch(() => scramble, async () => {
  expanded.value = false
  await nextTick()
  measure()
})

/** Times from 1:00:00.00 do not fit the display at the full size. */
const isLong = (text: string) => text.length > 8

const phase = computed(() => state.value.phase)
/** Inspection or a solve: only the timer is on the screen. */
const focused = computed(() => isFocused(state.value))

// The screen does not dim during inspection and a solve.
useScreenWakeLock(focused)

const display = computed(() => {
  const inspecting = inspectionElapsed.value !== null
  switch (phase.value) {
    case 'running':
      return formatResult(elapsed.value, 'time')
    case 'inspection':
      return inspectionCountdown(inspectionElapsed.value!)
    case 'holding':
    case 'ready':
      return inspecting ? inspectionCountdown(inspectionElapsed.value!) : '0.00'
    default:
      return mode === 'training' && phase.value === 'stopped' && last
        ? formatAttempt(last, 'time')
        : '0.00'
  }
})

const hint = computed(() => {
  const action = isTouch.value ? 'Удерживайте экран' : 'Удерживайте пробел'
  const elapsedMs = inspectionElapsed.value
  switch (phase.value) {
    case 'holding':
      return 'Приготовьтесь…'
    case 'ready':
      return 'Отпустите для старта'
    case 'running':
      return ''
    case 'inspection':
      if (elapsedMs! > 17_000) return 'Время инспекции вышло: DNF'
      if (elapsedMs! > 15_000) return 'Штраф +2 за инспекцию'
      if (elapsedMs! >= 12_000) return '12 секунд!'
      if (elapsedMs! >= 8_000) return '8 секунд!'
      return `${action}, чтобы начать сборку`
    default:
      if (scramble === null) return 'Готовим скрамбл…'
      return inspection.value
        ? `${isTouch.value ? 'Коснитесь экрана' : 'Нажмите пробел'}, чтобы начать инспекцию`
        : `${action}, чтобы начать`
  }
})

const isWarning = computed(() => {
  const elapsedMs = inspectionElapsed.value
  return phase.value !== 'running' && elapsedMs !== null && elapsedMs >= 8_000
})

// Manual entry

const manualText = ref('')
const manualError = ref('')

function submitManual() {
  const value = parseTimeInput(manualText.value)
  if (value === null) {
    manualError.value = 'Введите время, например 987 или 9.87'
    return
  }
  manualError.value = ''
  manualText.value = ''
  finish({ value, penalty: 'none' })
}

// Penalty choice and saving

const PENALTIES: { value: SuggestedPenalty; label: string }[] = [
  { value: 'none', label: 'OK' },
  { value: 'plus2', label: '+2' },
  { value: 'dnf', label: 'DNF' },
]

function setPenalty(penalty: SuggestedPenalty) {
  if (pending.value) {
    pending.value = { ...pending.value, penalty }
  }
}

const penaltyNote = computed(() => {
  switch (pending.value?.penalty) {
    case 'plus2':
      return '+2 секунды штрафа'
    case 'dnf':
      return 'Попытка не засчитана'
    default:
      return ''
  }
})

// Leaving during inspection or a solve

let leaveAnswer: ((leave: boolean) => void) | null = null
/** The moment of the leave attempt: the solve is stopped at it, not at the answer. */
let leaveMoment = 0

function confirmLeave() {
  if (!focused.value) {
    return true
  }
  // A repeated "back" while the dialog is open: the previous navigation is not waited for.
  leaveAnswer?.(false)
  leaveMoment = timerNow()
  // The finger or the space can not be released into the timer while the dialog is open.
  timer.cancel()
  leaveOpen.value = true
  return new Promise<boolean>((resolve) => {
    leaveAnswer = resolve
  })
}

// training: the solve is dropped. series: the stopped solve (or DNF without a time if it
// had not started: the scramble has been seen) becomes an unsaved attempt, the page
// keeps it, and the participant picks OK / +2 / DNF on returning to the series.
function interrupt() {
  if (mode === 'series') {
    pending.value = timer.abort(leaveMoment) ?? { value: null, penalty: 'dnf' }
  } else {
    timer.reset()
  }
  answerLeave(true)
}

function answerLeave(leave: boolean) {
  leaveOpen.value = false
  leaveAnswer?.(leave)
  leaveAnswer = null
}

// Esc and the backdrop close the dialog: stay on the screen.
watch(leaveOpen, (open) => {
  if (!open) {
    answerLeave(false)
  }
})

onBeforeRouteLeave(confirmLeave)
onBeforeRouteUpdate(confirmLeave)

// A reload or leaving the site: the browser asks itself.
useEventListener(window, 'beforeunload', (event: BeforeUnloadEvent) => {
  if (focused.value) {
    event.preventDefault()
  }
})

defineExpose({ reset: timer.reset })
</script>

<template>
  <section class="timer">
    <div v-show="!focused" class="timer__top">
      <slot name="header" />

      <div class="timer__scramble">
        <div class="timer__scramble-head">
          <span class="timer__scramble-title">{{ scrambleTitle }}</span>
          <button
            v-if="canRefresh"
            type="button"
            class="timer__icon-button"
            aria-label="Другой скрамбл"
            :disabled="scramble === null"
            @click="emit('refresh-scramble')"
          >
            <AppIcon name="refresh" :size="20" />
          </button>
        </div>
        <div
          ref="scrambleText"
          :class="[
            'timer__scramble-text',
            `timer__scramble-text--${scrambleSize}`,
            { 'timer__scramble-text--expanded': expanded },
          ]"
        >
          <template v-if="lines">
            <span v-for="(line, index) in lines" :key="index" class="timer__scramble-line">
              <template v-for="(piece, n) in line" :key="n">
                <span class="timer__scramble-piece">{{ piece }}</span>{{ ' ' }}
              </template>
            </span>
          </template>
          <template v-else>Генерируем скрамбл…</template>
        </div>
        <button
          v-if="overflows"
          type="button"
          class="timer__expand"
          :aria-expanded="expanded"
          @click="expanded = !expanded"
        >
          <AppIcon :name="expanded ? 'expand-less' : 'expand-more'" :size="20" />
          {{ expanded ? 'Свернуть скрамбл' : 'Развернуть скрамбл' }}
        </button>
      </div>

      <div class="timer__controls">
        <label v-if="!manual" class="timer__switch">
          <input v-model="inspection" type="checkbox" :disabled="phase !== 'idle' && phase !== 'stopped'" />
          <span>Инспекция 15 с</span>
        </label>
        <div class="timer__segments" role="group" aria-label="Способ ввода">
          <button
            type="button"
            :class="['timer__segment', { 'timer__segment--active': !manual }]"
            :aria-pressed="!manual"
            @click="manual = false"
          >
            Таймер
          </button>
          <button
            type="button"
            :class="['timer__segment', { 'timer__segment--active': manual }]"
            :aria-pressed="manual"
            @click="manual = true"
          >
            Ручной
          </button>
        </div>
      </div>

      <slot name="actions" />
    </div>

    <div v-if="pending" class="timer__review">
      <p class="timer__review-title">
        <AppIcon name="check" :size="20" />
        Время зафиксировано
      </p>
      <p
        :class="[
          'timer__display',
          {
            'timer__display--dnf': pending.penalty === 'dnf',
            'timer__display--long': isLong(formatAttempt(pending, 'time')),
          },
        ]"
      >
        {{ formatAttempt(pending, 'time') }}
      </p>
      <p v-if="penaltyNote" class="timer__penalty-note">{{ penaltyNote }}</p>
      <div class="timer__penalties" role="group" aria-label="Штраф">
        <button
          v-for="option in PENALTIES"
          :key="option.value"
          type="button"
          :class="[
            'timer__penalty',
            `timer__penalty--${option.value}`,
            { 'timer__penalty--active': pending.penalty === option.value },
          ]"
          :aria-pressed="pending.penalty === option.value"
          :disabled="saving || (option.value !== 'dnf' && pending.value === null)"
          @click="setPenalty(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
      <AppButton class="timer__save" :loading="saving" @click="emit('save', pending)">
        {{ saving ? 'Сохраняем…' : 'Сохранить попытку' }}
      </AppButton>
      <slot name="review" />
    </div>

    <form v-else-if="manual" class="timer__manual" @submit.prevent="submitManual">
      <label class="timer__manual-label" for="timer-manual-input">Время сборки</label>
      <input
        id="timer-manual-input"
        v-model="manualText"
        class="timer__manual-input"
        inputmode="decimal"
        autocomplete="off"
        placeholder="0.00"
        :aria-invalid="Boolean(manualError)"
        :disabled="scramble === null || saving"
      />
      <p v-if="manualError" class="timer__manual-error">{{ manualError }}</p>
      <p v-else class="timer__hint">Например, 987 или 9.87, после минуты — 1:02.45</p>
      <AppButton type="submit" :disabled="scramble === null || saving">
        {{ mode === 'series' ? 'Далее' : 'Записать' }}
      </AppButton>
    </form>

    <p v-else-if="expanded" class="timer__collapsed">Чтобы начать, сверните скрамбл</p>

    <div
      v-else
      :class="['timer__zone', `timer__zone--${phase}`]"
      @pointerdown="onZonePointerDown"
      @contextmenu.prevent
    >
      <p
        :class="[
          'timer__display',
          {
            'timer__display--dnf': mode === 'training' && phase === 'stopped' && last?.penalty === 'dnf',
            'timer__display--long': isLong(display),
          },
        ]"
        aria-live="off"
      >
        {{ display }}
      </p>
      <p :class="['timer__hint', { 'timer__hint--warning': isWarning }]" aria-live="polite">
        {{ hint }}
      </p>
    </div>

    <div v-if="$slots.last" v-show="!focused" class="timer__last">
      <slot name="last" />
    </div>

    <ConfirmDialog
      v-model:open="leaveOpen"
      title="Идёт сборка. Прервать?"
      confirm-label="Прервать"
      cancel-label="Продолжить"
      danger
      @confirm="interrupt"
    >
      {{
        mode === 'series'
          ? 'Таймер остановится. Вернувшись к серии, выберите OK, +2 или DNF и сохраните попытку.'
          : 'Сборка не попадёт в тренировочную сессию.'
      }}
    </ConfirmDialog>
  </section>
</template>

<style scoped>
.timer {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--space-3);
  min-height: 0;
}

.timer__top {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.timer__scramble {
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.timer__scramble-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: 28px;
}

.timer__scramble-title {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-label);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.timer__scramble-text {
  position: relative;
  /* With the timer zone (at least 260px) everything fits a phone screen without page scroll. */
  max-height: 25dvh;
  margin-top: var(--space-1);
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 17px;
  line-height: 1.5;
  word-spacing: 0.15em;
  overscroll-behavior: contain;
  /* A shadow at the bottom while there is more text below: the first layer
     scrolls with the text and covers the shadow at the end. */
  background:
    linear-gradient(transparent, var(--color-surface) 70%) center bottom / 100% 24px no-repeat local,
    linear-gradient(transparent, var(--color-border)) center bottom / 100% 12px no-repeat scroll;
}

.timer__scramble-text--medium {
  font-size: 15px;
}

.timer__scramble-text--small {
  font-size: 13px;
  line-height: 1.45;
  word-spacing: 0.05em;
}

.timer__scramble-text--expanded {
  max-height: none;
}

.timer__scramble-line {
  display: block;
}

/* A move, or a Square-1 piece "(1, -3) /": the line wraps only between pieces. */
.timer__scramble-piece {
  white-space: nowrap;
}

.timer__expand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  width: 100%;
  min-height: 36px;
  margin-top: var(--space-2);
  background: none;
  border: 0;
  border-top: 1px solid var(--color-border);
  color: var(--color-primary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.timer__collapsed {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}

/* Megaminx: seven lines of the same length, the font is fitted to the block width
   so that a line does not wrap. */
.timer__scramble-text--lines {
  container-type: inline-size;
  word-spacing: 0;
}

.timer__scramble-text--lines .timer__scramble-line {
  font-size: min(15px, 100cqi / 26);
  white-space: pre;
}

.timer__icon-button {
  display: flex;
  padding: var(--space-1);
  background: none;
  border: 0;
  border-radius: var(--radius-button);
  color: var(--color-primary);
  cursor: pointer;
}

.timer__icon-button:disabled {
  color: var(--color-text-secondary);
  cursor: default;
}

.timer__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.timer__switch {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.timer__switch input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
}

.timer__segments {
  display: inline-flex;
  margin-left: auto;
  padding: 2px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
}

.timer__segment {
  height: 32px;
  padding: 0 var(--space-3);
  background: none;
  border: 0;
  border-radius: 6px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
  cursor: pointer;
}

.timer__segment--active {
  background: var(--color-primary);
  color: var(--color-on-primary);
}

.timer__zone,
.timer__review,
.timer__manual {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  min-height: 260px;
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
}

.timer__zone {
  cursor: pointer;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}

.timer__display {
  font-family: var(--font-mono);
  font-size: clamp(56px, 18vw, 96px);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.timer__display--long {
  font-size: clamp(40px, 13vw, 72px);
}

.timer__zone--holding .timer__display {
  color: var(--color-text-secondary);
}

.timer__zone--ready .timer__display {
  color: var(--color-primary);
}

.timer__display--dnf {
  color: var(--color-dnf);
}

.timer__hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
  text-align: center;
}

.timer__last {
  display: flex;
  justify-content: center;
}

.timer__hint--warning {
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
}

.timer__review-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-primary);
  font-weight: var(--font-weight-label);
}

.timer__penalty-note {
  color: var(--color-text-secondary);
  font-size: var(--font-size-label);
}

.timer__penalties {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  width: 100%;
  max-width: 360px;
}

.timer__penalty {
  height: var(--control-height);
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-heading);
  cursor: pointer;
}

.timer__penalty--dnf {
  color: var(--color-dnf);
}

.timer__penalty--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-on-primary);
}

/* A selected DNF gets a red border, not a red fill (as the danger AppButton). */
.timer__penalty--dnf.timer__penalty--active {
  background: var(--color-surface);
  border: 2px solid var(--color-dnf);
  color: var(--color-dnf);
}

.timer__penalty:disabled {
  opacity: 0.5;
  cursor: default;
}

.timer__save {
  width: 100%;
  max-width: 360px;
}

.timer__manual {
  align-items: stretch;
  justify-content: flex-start;
}

.timer__manual-label {
  font-size: var(--font-size-label);
  font-weight: var(--font-weight-label);
}

.timer__manual-input {
  height: 64px;
  padding: 0 var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-button);
  font-family: var(--font-mono);
  font-size: 32px;
  font-variant-numeric: tabular-nums;
  text-align: center;
  outline: none;
}

.timer__manual-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.timer__manual-input[aria-invalid='true'] {
  border-color: var(--color-danger);
}

.timer__manual-error {
  color: var(--color-danger);
  font-size: var(--font-size-label);
}
</style>

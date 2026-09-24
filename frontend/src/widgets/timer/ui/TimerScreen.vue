<script setup lang="ts">
import { useLocalStorage, useMediaQuery } from '@vueuse/core'
import { computed, ref, toRef } from 'vue'
import { formatAttempt, formatResult, parseTimeInput } from '@/shared/lib'
import { AppButton, AppIcon } from '@/shared/ui'
import type { SuggestedPenalty } from '../model/machine'
import { inspectionCountdown, useTimer, type StoppedSolve } from '../model/useTimer'

/** Результат сборки: время без штрафа и штраф. У DNF время может быть. */
export interface TimerResult {
  value: number | null
  penalty: SuggestedPenalty
}

// Экран таймера (макет timer_series): сверху скрамбл и управление,
// всё остальное — зона касания.
//
// training — сборка сразу уходит в solved, страница сохраняет её в сессию;
// last — последняя сборка сессии, слот last — строка «Последняя» под таймером.
// series — после сборки участник выбирает OK / +2 / DNF и нажимает
// «Сохранить попытку» (save). Несохранённый результат — v-model:pending,
// чтобы страница могла пережить с ним перезагрузку.
const pending = defineModel<TimerResult | null>('pending', { default: null })

const { mode, scramble, saving = false, last = null } = defineProps<{
  mode: 'training' | 'series'
  /** null — скрамбл ещё генерируется или загружается. */
  scramble: string | null
  /** Заголовок блока скрамбла: «Тренировка», «Попытка 3 из 5». */
  scrambleTitle: string
  /** Кнопка нового скрамбла (только в тренировке). */
  canRefresh?: boolean
  saving?: boolean
  /** Последняя сборка тренировки: показывается на табло сразу после сборки. */
  last?: TimerResult | null
}>()

const emit = defineEmits<{
  solved: [result: TimerResult]
  save: [result: TimerResult]
  'refresh-scramble': []
}>()

// Настройки таймера — удобство этого устройства, хранятся в браузере.
const inspection = useLocalStorage('timer-inspection', false)
const manual = useLocalStorage('timer-manual', false)
const isTouch = useMediaQuery('(pointer: coarse)')

const enabled = computed(
  () => !manual.value && scramble !== null && !saving && pending.value === null,
)

const timer = useTimer({
  inspection: toRef(inspection),
  enabled,
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

const phase = computed(() => state.value.phase)
const isRunning = computed(() => phase.value === 'running')

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

// Ручной ввод

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

// Выбор штрафа и сохранение

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

defineExpose({ reset: timer.reset })
</script>

<template>
  <section :class="['timer', { 'timer--running': isRunning }]">
    <div class="timer__top">
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
        <p class="timer__scramble-text">{{ scramble ?? 'Генерируем скрамбл…' }}</p>
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
      <p :class="['timer__display', { 'timer__display--dnf': pending.penalty === 'dnf' }]">
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

    <div v-if="$slots.last" class="timer__last">
      <slot name="last" />
    </div>
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

/* Во время сборки ничего не отвлекает, но раскладка не прыгает. */
.timer--running .timer__top,
.timer--running .timer__last {
  visibility: hidden;
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
  margin-top: var(--space-1);
  font-family: var(--font-mono);
  font-size: 17px;
  line-height: 1.5;
  word-spacing: 0.15em;
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

/* Выбранный DNF — красная рамка, а не красная заливка (DESIGN.md, AppButton). */
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

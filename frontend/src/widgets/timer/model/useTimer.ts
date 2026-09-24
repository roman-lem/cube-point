import { useEventListener, useRafFn } from '@vueuse/core'
import { computed, ref, type Ref } from 'vue'
import {
  HOLD_MS,
  INSPECTION_MS,
  initialState,
  transition,
  type SuggestedPenalty,
  type TimerEvent,
} from './machine'

export interface StoppedSolve {
  /** Время сборки в сотых долях секунды. */
  value: number
  /** Штраф за инспекцию, участник может его сменить. */
  penalty: SuggestedPenalty
}

const ACTIVE_PHASES = ['inspection', 'holding', 'ready', 'running'] as const

/**
 * Таймер: связывает машину состояний с касаниями, пробелом и часами.
 *
 * Время берётся из performance.now() в момент события. Касание начинается
 * на зоне таймера (onZonePointerDown), а во время сборки остановить таймер
 * можно касанием или любой клавишей где угодно.
 */
export function useTimer(options: {
  inspection: Ref<boolean>
  /** Можно ли сейчас начать сборку (нет ручного ввода, скрамбл готов и т. п.). */
  enabled: Ref<boolean>
  onStop: (solve: StoppedSolve) => void
}) {
  const state = ref(initialState())
  const now = ref(0)

  function dispatch(type: TimerEvent['type']) {
    const moment = performance.now()
    now.value = moment
    const before = state.value.phase
    state.value = transition(state.value, { type, now: moment }, {
      inspection: options.inspection.value,
    })
    if (before === 'running' && state.value.phase === 'stopped') {
      options.onStop({ value: state.value.result, penalty: state.value.inspectionPenalty })
    }
    if (before !== 'holding' && state.value.phase === 'holding') {
      // Переход holding → ready — по таймауту, а не по кадрам: они не приходят,
      // пока вкладка не видна или браузер занят.
      setTimeout(() => dispatch('tick'), HOLD_MS)
    }
    if (isActive.value) {
      clock.resume()
    }
  }

  const isActive = computed(() =>
    (ACTIVE_PHASES as readonly string[]).includes(state.value.phase),
  )

  // Часы для отображения.
  const clock = useRafFn(
    () => {
      now.value = performance.now()
      if (!isActive.value) {
        clock.pause()
      }
    },
    { immediate: false },
  )

  /** Во время сборки остановка работает всегда; начать можно только когда разрешено. */
  function canPress() {
    return state.value.phase === 'running' || (options.enabled.value && !isDialogOpen())
  }

  function onZonePointerDown(event: PointerEvent) {
    if (event.button !== 0 || !canPress()) {
      return
    }
    event.preventDefault()
    dispatch('press')
  }

  useEventListener(window, 'pointerdown', (event: PointerEvent) => {
    // Остановка касанием в любом месте экрана. Касание зоны таймера уже
    // обработано в onZonePointerDown: там фаза стала stopped.
    if (state.value.phase === 'running') {
      event.preventDefault()
      dispatch('press')
    }
  })
  useEventListener(window, ['pointerup', 'pointercancel'], () => dispatch('release'))

  useEventListener(window, 'keydown', (event: KeyboardEvent) => {
    if (state.value.phase === 'running') {
      // Любая клавиша останавливает сборку.
      event.preventDefault()
      dispatch('press')
      return
    }
    if (event.code !== 'Space' || isTyping(event) || !canPress()) {
      return
    }
    // Пробел не должен нажимать кнопку в фокусе или прокручивать страницу.
    event.preventDefault()
    if (!event.repeat) {
      dispatch('press')
    }
  })
  useEventListener(window, 'keyup', (event: KeyboardEvent) => {
    if (event.code === 'Space') {
      dispatch('release')
    }
  })

  /** Секунды инспекции для показа: 15 … 1, затем +2 и DNF. */
  const inspectionElapsed = computed(() =>
    state.value.inspectionStart === null ? null : now.value - state.value.inspectionStart,
  )

  /** Текущее время сборки в сотых. */
  const elapsed = computed(() =>
    state.value.phase === 'running' ? Math.floor((now.value - state.value.solveStart) / 10) : 0,
  )

  function reset() {
    state.value = initialState()
  }

  return { state, elapsed, inspectionElapsed, isActive, onZonePointerDown, reset }
}

export function inspectionCountdown(elapsedMs: number): string {
  if (elapsedMs <= INSPECTION_MS) {
    return String(Math.ceil((INSPECTION_MS - elapsedMs) / 1000))
  }
  return elapsedMs <= INSPECTION_MS + 2000 ? '+2' : 'DNF'
}

function isTyping(event: KeyboardEvent) {
  const target = event.target
  return (
    target instanceof Element && target.closest('input, textarea, select, [contenteditable]') !== null
  )
}

function isDialogOpen() {
  return document.querySelector('dialog[open]') !== null
}

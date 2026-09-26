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
  /** Solve time in hundredths of a second. */
  value: number
  /** Inspection penalty, the participant can change it. */
  penalty: SuggestedPenalty
}

const ACTIVE_PHASES = ['inspection', 'holding', 'ready', 'running'] as const

/**
 * Timer: connects the state machine with touches, the space bar and the clock.
 *
 * Time is taken from performance.now() at the event. A touch starts
 * on the timer zone (onZonePointerDown), and during a solve the timer can be stopped
 * by a touch or any key anywhere.
 */
export function useTimer(options: {
  inspection: Ref<boolean>
  /** Whether a solve can start now (no manual entry, scramble ready, etc.). */
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
      // The holding → ready transition is by timeout, not by frames: they do not come
      // while the tab is hidden or the browser is busy.
      setTimeout(() => dispatch('tick'), HOLD_MS)
    }
    if (isActive.value) {
      clock.resume()
    }
  }

  const isActive = computed(() =>
    (ACTIVE_PHASES as readonly string[]).includes(state.value.phase),
  )

  // Clock for display.
  const clock = useRafFn(
    () => {
      now.value = performance.now()
      if (!isActive.value) {
        clock.pause()
      }
    },
    { immediate: false },
  )

  /** During a solve stopping always works; starting only when allowed. */
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
    // Stopping with a touch anywhere on the screen. A touch on the timer zone has already
    // been handled in onZonePointerDown: the phase became stopped there.
    if (state.value.phase === 'running') {
      event.preventDefault()
      dispatch('press')
    }
  })
  useEventListener(window, ['pointerup', 'pointercancel'], () => dispatch('release'))

  useEventListener(window, 'keydown', (event: KeyboardEvent) => {
    if (state.value.phase === 'running') {
      // Any key stops the solve.
      event.preventDefault()
      dispatch('press')
      return
    }
    if (event.code !== 'Space' || isTyping(event) || !canPress()) {
      return
    }
    // Space must not press the focused button or scroll the page.
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

  /** Inspection seconds for display: 15 … 1, then +2 and DNF. */
  const inspectionElapsed = computed(() =>
    state.value.inspectionStart === null ? null : now.value - state.value.inspectionStart,
  )

  /** Current solve time in hundredths. */
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

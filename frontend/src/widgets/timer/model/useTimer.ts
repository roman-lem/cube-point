import { useEventListener, useRafFn } from '@vueuse/core'
import { storeToRefs } from 'pinia'
import { computed, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import {
  HOLD_MS,
  INSPECTION_MS,
  initialState,
  transition,
  type SuggestedPenalty,
  type TimerEvent,
} from './machine'
import { timerNow } from './saved'
import { useTimerStore } from './store'

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
 * The state is in the timer store, so leaving the screen or reloading the page
 * does not reset it. Time is taken from timerNow() at the event. A touch starts
 * on the timer zone (onZonePointerDown), and during a solve the timer can be stopped
 * by a touch or any key anywhere.
 */
export function useTimer(options: {
  /** Whose solve it is: `training:<event_id>` or `series:<series_id>:<attempt>`. */
  owner: Ref<string>
  inspection: Ref<boolean>
  /** Whether a solve can start now (no manual entry, scramble ready, etc.). */
  enabled: Ref<boolean>
  /** The leave confirmation is open: touches and keys go to it, not to the timer. */
  blocked: Ref<boolean>
  onStop: (solve: StoppedSolve) => void
}) {
  const store = useTimerStore()
  const { state } = storeToRefs(store)
  const now = ref(timerNow())

  // A solve of this screen continues after returning to it, a solve of another one is dropped.
  watch(options.owner, (key) => store.claim(key), { immediate: true })
  onMounted(() => {
    store.screenOpen = true
  })
  onUnmounted(() => {
    store.screenOpen = false
  })

  function dispatch(type: TimerEvent['type'], moment = timerNow()) {
    now.value = moment
    const before = state.value.phase
    state.value = transition(state.value, { type, now: moment }, {
      inspection: options.inspection.value,
    })
    // abort returns the stopped solve itself: the screen decides what to do with it.
    if (before === 'running' && state.value.phase === 'stopped' && type !== 'abort') {
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

  // Holding does not survive leaving the screen: the finger is not held any more.
  // An inspection or a solve goes on, the clock starts again.
  dispatch('cancel')

  // The tab went to the background while held: the start is cancelled.
  useEventListener(document, 'visibilitychange', () => {
    if (document.hidden) {
      dispatch('cancel')
    }
  })

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
    if (options.blocked.value) {
      return
    }
    // Stopping with a touch anywhere on the screen. A touch on the timer zone has already
    // been handled in onZonePointerDown: the phase became stopped there.
    if (state.value.phase === 'running') {
      event.preventDefault()
      dispatch('press')
    }
  })
  useEventListener(window, ['pointerup', 'pointercancel'], () => dispatch('release'))

  useEventListener(window, 'keydown', (event: KeyboardEvent) => {
    if (options.blocked.value) {
      return
    }
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

  /**
   * Interrupts the solve when leaving the screen at `moment`: returns the stopped solve,
   * or null if the solve had not started yet (the timer goes back to idle).
   */
  function abort(moment: number): StoppedSolve | null {
    const wasRunning = state.value.phase === 'running'
    dispatch('abort', moment)
    return wasRunning ? { value: state.value.result, penalty: state.value.inspectionPenalty } : null
  }

  return {
    state, elapsed, inspectionElapsed, isActive, onZonePointerDown, reset, abort,
    cancel: () => dispatch('cancel'),
  }
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

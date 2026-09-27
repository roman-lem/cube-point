import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { initialState, isFocused, type TimerState } from './machine'
import { parseSavedTimer, serializeSavedTimer } from './saved'

const STORAGE_KEY = 'timer-state'

/**
 * Timer state outside the component: survives leaving the timer screen, and through
 * sessionStorage a reload or a tab unloaded by the browser. The time is counted from
 * the saved start moments, so on return the timer goes on with the right time.
 */
export const useTimerStore = defineStore('timer', () => {
  const saved = read()
  /** Whose solve it is (see SavedTimer.owner); null until a timer screen opens. */
  const owner = ref<string | null>(saved?.owner ?? null)
  const state = ref<TimerState>(saved?.state ?? initialState())

  /** A timer screen is open (the state is shown only there). */
  const screenOpen = ref(false)

  /** Inspection or solve in progress on the open screen: the app hides everything except the timer. */
  const focused = computed(() => screenOpen.value && isFocused(state.value))

  // The state changes only on events, so it is saved right away.
  watch([owner, state], () => {
    if (owner.value === null) {
      return
    }
    try {
      sessionStorage.setItem(STORAGE_KEY, serializeSavedTimer({ owner: owner.value, state: state.value }))
    } catch {
      // Storage is unavailable (private mode): the timer just will not survive a reload.
    }
  }, { flush: 'sync' })

  /** The timer screen of `key` opens: a solve of another screen is not continued. */
  function claim(key: string) {
    if (owner.value !== key) {
      owner.value = key
      state.value = initialState()
    }
  }

  return { owner, state, screenOpen, focused, claim }
})

function read() {
  try {
    return parseSavedTimer(sessionStorage.getItem(STORAGE_KEY))
  } catch {
    return null
  }
}

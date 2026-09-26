import { useIntervalFn } from '@vueuse/core'
import { computed, ref, type Ref } from 'vue'
import type { FmcAttemptState } from '@/entities/series'

/**
 * Milliseconds left until the attempt deadline by the server clock.
 * The clock difference is computed from server_now when the state is received.
 */
export function useFmcClock(state: Ref<FmcAttemptState | null | undefined>) {
  const now = ref(Date.now())
  useIntervalFn(() => (now.value = Date.now()), 250)
  const offset = computed(() =>
    state.value ? Date.parse(state.value.server_now) - Date.now() : 0,
  )
  const remaining = computed(() => {
    if (!state.value) {
      return null
    }
    return Math.max(0, Date.parse(state.value.deadline) - (now.value + offset.value))
  })
  return { remaining }
}

/** Remaining time: 47:12. */
export function formatCountdown(ms: number): string {
  const seconds = Math.ceil(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  return `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

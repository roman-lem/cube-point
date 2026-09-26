import { useEventListener } from '@vueuse/core'
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import type { MySeries } from '@/entities/series'
import { ApiError } from '@/shared/api'
import { saveFmcDraft } from '../api/fmcApi'

export type DraftStatus = 'saved' | 'saving' | 'unsaved'

// The draft goes to the server a second after a change, and immediately when
// the tab is hidden. On a network error it retries until the solution is saved.
const DEBOUNCE_MS = 1000
const RETRY_MS = 3000

/**
 * Autosave of the FMC solution draft while enabled (the attempt is running and not frozen).
 * saved is the text already on the server.
 */
export function useDraftAutosave(
  series: Ref<MySeries | null>,
  solution: Ref<string>,
  enabled: Ref<boolean>,
) {
  const saved = ref(series.value?.next_attempt?.fmc?.draft ?? '')
  const status = ref<DraftStatus>('saved')
  let timer: ReturnType<typeof setTimeout> | undefined
  let inFlight: Promise<void> | null = null

  function schedule(delay: number) {
    clearTimeout(timer)
    timer = setTimeout(save, delay)
  }

  async function save() {
    clearTimeout(timer)
    if (inFlight) {
      // Wait for the current request and send the fresh text right after it.
      await inFlight
    }
    const text = solution.value
    if (!enabled.value || !series.value) {
      return
    }
    if (text === saved.value) {
      status.value = 'saved'
      return
    }
    status.value = 'saving'
    inFlight = saveFmcDraft(series.value, text)
      .then(() => {
        saved.value = text
        status.value = solution.value === text ? 'saved' : 'unsaved'
        if (status.value === 'unsaved') schedule(DEBOUNCE_MS)
      })
      .catch((e) => {
        status.value = 'unsaved'
        // time_over, frozen and other server rejections are pointless to retry.
        if (e instanceof ApiError && e.code === 'network_error') schedule(RETRY_MS)
      })
      .finally(() => {
        inFlight = null
      })
    await inFlight
  }

  watch(solution, (text) => {
    if (enabled.value && text !== saved.value) {
      status.value = 'unsaved'
      schedule(DEBOUNCE_MS)
    }
  })

  /** When the server sent a new attempt state (start, back to solution). */
  function reset(text: string) {
    clearTimeout(timer)
    saved.value = text
    status.value = solution.value === text ? 'saved' : 'unsaved'
  }

  useEventListener(document, 'visibilitychange', () => {
    if (document.visibilityState === 'hidden') save()
  })
  // Do not lose the last moves when leaving the screen.
  onBeforeUnmount(save)

  return { status, flush: save, reset }
}

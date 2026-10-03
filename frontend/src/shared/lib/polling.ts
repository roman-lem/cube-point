import { useDocumentVisibility, useIntervalFn } from '@vueuse/core'
import { watch } from 'vue'

/**
 * Loading where only the response of the latest request is applied:
 * a slow old response does not overwrite fresh data.
 * invalidate() drops the responses of requests already sent,
 * when fresher data came from elsewhere (e.g. after a save).
 */
export function latestLoader<T>(
  fetch: () => Promise<T>,
  apply: (data: T) => void,
  onError: (e: unknown) => void,
) {
  let latest = 0

  async function load() {
    const id = ++latest
    try {
      const data = await fetch()
      if (id === latest) apply(data)
    } catch (e) {
      if (id === latest) onError(e)
    }
  }

  return { load, invalidate: () => { latest++ } }
}

/**
 * Calls load every intervalMs while active() is true and the tab is visible.
 * On return to the tab it loads right away. A new tick waits for the previous load.
 * The interval stops when the component is unmounted.
 */
export function usePolling(
  load: () => Promise<unknown>,
  intervalMs: number,
  active: () => boolean = () => true,
) {
  const visibility = useDocumentVisibility()
  let busy = false

  async function poll() {
    if (busy || visibility.value !== 'visible' || !active()) return
    busy = true
    try {
      await load()
    } finally {
      busy = false
    }
  }

  useIntervalFn(poll, intervalMs)
  watch(visibility, (value) => {
    if (value === 'visible') poll()
  })
}

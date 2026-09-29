import { useWakeLock } from '@vueuse/core'
import { watch, type Ref } from 'vue'

/**
 * Keeps the screen on while `active` is true (Screen Wake Lock API).
 *
 * The browser releases the lock when the tab goes to the background, useWakeLock
 * requests it again on return. The lock is released when the component is unmounted.
 * Without the API, or if the browser refuses (e.g. battery saver), the screen
 * just works as usual.
 */
export function useScreenWakeLock(active: Ref<boolean>) {
  const wakeLock = useWakeLock()

  watch(
    active,
    async (on) => {
      try {
        if (on) {
          await wakeLock.request('screen')
          // `active` became false while the request was in flight.
          if (!active.value) {
            await wakeLock.release()
          }
        } else {
          await wakeLock.release()
        }
      } catch {
        // Not supported or not allowed: the screen dims as usual.
      }
    },
    { immediate: true },
  )
}

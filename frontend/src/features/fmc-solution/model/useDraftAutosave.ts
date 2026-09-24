import { useEventListener } from '@vueuse/core'
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import type { MySeries } from '@/entities/series'
import { ApiError } from '@/shared/api'
import { saveFmcDraft } from '../api/fmcApi'

export type DraftStatus = 'saved' | 'saving' | 'unsaved'

// Черновик уходит на сервер через секунду после изменения, при сворачивании
// вкладки — сразу. При ошибке сети повторяем, пока решение не сохранится.
const DEBOUNCE_MS = 1000
const RETRY_MS = 3000

/**
 * Автосохранение черновика решения FMC, пока enabled (попытка идёт и не заморожена).
 * saved — текст, который уже есть на сервере.
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
      // Дождёмся текущего запроса и отправим свежий текст следом.
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
        // time_over, frozen и прочие отказы сервера повторять бессмысленно.
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

  /** Когда сервер прислал новое состояние попытки (старт, возврат к решению). */
  function reset(text: string) {
    clearTimeout(timer)
    saved.value = text
    status.value = solution.value === text ? 'saved' : 'unsaved'
  }

  useEventListener(document, 'visibilitychange', () => {
    if (document.visibilityState === 'hidden') save()
  })
  // Уходя с экрана, не теряем последние ходы.
  onBeforeUnmount(save)

  return { status, flush: save, reset }
}

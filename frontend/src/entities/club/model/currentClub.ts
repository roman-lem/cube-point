import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchClubs } from '../api/clubApi'
import type { ClubSummary } from './types'

const STORAGE_KEY = 'lastClubId'

function readStoredId(): number | null {
  try {
    const value = Number(localStorage.getItem(STORAGE_KEY))
    return Number.isInteger(value) && value > 0 ? value : null
  } catch {
    return null
  }
}

/**
 * Клуб, в котором сейчас человек: на него ведут вкладки «Клуб», «Рекорды»
 * и «Участники». Это последний открытый клуб (запоминается в браузере),
 * а если его нет — первый из списка.
 */
export const useCurrentClubStore = defineStore('currentClub', () => {
  const clubs = ref<ClubSummary[]>([])
  const storedId = ref(readStoredId())
  let loading: Promise<void> | null = null

  const club = computed(
    () => clubs.value.find((c) => c.id === storedId.value) ?? clubs.value[0] ?? null,
  )
  const clubId = computed(() => club.value?.id ?? storedId.value)
  const isLive = computed(() => club.value?.live_meetup_id != null)

  /** Загружает список клубов; повторно — только с reload (например, после запуска встречи). */
  function load(reload = false): Promise<void> {
    if (clubs.value.length > 0 && !reload) {
      return Promise.resolve()
    }
    loading ??= fetchClubs()
      .then((items) => {
        clubs.value = items
      })
      .catch(() => {
        // Без списка навигация просто ведёт на последний клуб.
      })
      .finally(() => {
        loading = null
      })
    return loading
  }

  function setClubId(id: number) {
    storedId.value = id
    try {
      localStorage.setItem(STORAGE_KEY, String(id))
    } catch {
      // Хранилище недоступно (приватный режим) — просто не запоминаем.
    }
  }

  return { clubs, club, clubId, isLive, load, setClubId }
})

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
 * The club the person is currently in: the "Club", "Records" and "Members"
 * tabs lead to it. It is the last opened club (remembered in the browser),
 * or the first one in the list if there is none.
 */
export const useCurrentClubStore = defineStore('currentClub', () => {
  const clubs = ref<ClubSummary[]>([])
  const loaded = ref(false)
  const storedId = ref(readStoredId())
  let loading: Promise<void> | null = null

  const club = computed(
    () => clubs.value.find((c) => c.id === storedId.value) ?? clubs.value[0] ?? null,
  )
  // The remembered id only until the list is loaded: the club may have been deleted.
  const clubId = computed(() => club.value?.id ?? (loaded.value ? null : storedId.value))
  const isLive = computed(() => club.value?.live_meetup_id != null)

  /** Loads the club list; again only with reload (e.g. after a meetup starts). */
  function load(reload = false): Promise<void> {
    if (loaded.value && !reload) {
      return Promise.resolve()
    }
    loading ??= fetchClubs()
      .then((items) => {
        clubs.value = items
        loaded.value = true
      })
      .catch(() => {
        // Without the list, navigation simply leads to the last club.
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
      // Storage is unavailable (private mode): just do not remember.
    }
  }

  return { clubs, club, clubId, isLive, load, setClubId }
})

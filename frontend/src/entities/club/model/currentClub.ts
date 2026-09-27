import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchClubs, fetchHomeClubId } from '../api/clubApi'
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
 * tabs lead to it.
 *
 * - The viewed club (in memory): any club whose page was opened in this visit,
 *   including someone else's club from the club list.
 * - The remembered club (in the browser): the last opened club the logged-in user
 *   is a member of (for a guest, any). The next visit starts from it: the site root
 *   and the tabs ask the server for the home club with it (GET /api/auth/home-club),
 *   and the server checks that the user is still a member there.
 */
export const useCurrentClubStore = defineStore('currentClub', () => {
  const clubs = ref<ClubSummary[]>([])
  const loaded = ref(false)
  // undefined: not told yet (the first setUserId always loads).
  const userId = ref<number | null | undefined>(undefined)
  const viewedId = ref<number | null>(null)
  const rememberedId = ref(readStoredId())
  const homeClubId = ref<number | null>(null)
  let loading: Promise<void> | null = null
  let loadingFor: number | null | undefined

  const find = (id: number | null) => clubs.value.find((c) => c.id === id)
  const club = computed(() => {
    if (userId.value) {
      return find(viewedId.value) ?? find(homeClubId.value) ?? null
    }
    return find(viewedId.value) ?? find(rememberedId.value) ?? clubs.value[0] ?? null
  })
  // Until the list is loaded, the viewed club (or the remembered one for a guest):
  // the club may have been deleted. Without a club the tabs lead to the site root.
  const unloadedId = computed(() => viewedId.value ?? (userId.value ? null : rememberedId.value))
  const clubId = computed(() => club.value?.id ?? (loaded.value ? null : unloadedId.value))
  const isLive = computed(() => club.value?.live_meetup_id != null)

  /** Loads the club list; again only with reload (e.g. after a meetup starts). */
  function load(reload = false): Promise<void> {
    if (loaded.value && !reload) {
      return Promise.resolve()
    }
    // A request already running for the same user is enough.
    if (loading && loadingFor === userId.value) {
      return loading
    }
    const forUser = userId.value
    const request: Promise<void> = Promise.all([
      fetchClubs(),
      forUser ? fetchHomeClubId(rememberedId.value) : null,
    ])
      .then(([items, homeId]) => {
        // The user changed while loading: the newer request fills everything in.
        if (forUser !== userId.value) {
          return
        }
        clubs.value = items
        homeClubId.value = homeId
        loaded.value = true
        // A club opened before the list arrived is remembered now.
        if (viewedId.value) {
          remember(viewedId.value)
        }
      })
      .catch(() => {
        // Without the list, navigation simply leads to the last club.
      })
      .finally(() => {
        if (loading === request) {
          loading = null
        }
      })
    loading = request
    loadingFor = forUser
    return request
  }

  /** Who is logged in (null for a guest): on a change the clubs are reloaded, my_role changes. */
  function setUserId(id: number | null) {
    if (id === userId.value) {
      return
    }
    userId.value = id
    viewedId.value = null
    load(true)
  }

  function remember(id: number) {
    if (userId.value && !find(id)?.my_role) {
      return
    }
    rememberedId.value = id
    try {
      localStorage.setItem(STORAGE_KEY, String(id))
    } catch {
      // Storage is unavailable (private mode): just do not remember.
    }
  }

  /** A page of the club was opened. */
  function setClubId(id: number) {
    viewedId.value = id
    if (loaded.value) {
      remember(id)
    }
  }

  return { clubs, loaded, club, clubId, isLive, rememberedId, load, setUserId, setClubId }
})

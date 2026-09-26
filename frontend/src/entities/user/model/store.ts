import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchMe } from '../api/me'
import type { User } from './types'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const loaded = ref(false)
  let loading: Promise<void> | null = null

  const isAuthenticated = computed(() => user.value !== null)

  /** Loads the user once per app start (called by the router). */
  function ensureLoaded(): Promise<void> {
    if (loaded.value) {
      return Promise.resolve()
    }
    loading ??= fetchMe()
      .then((me) => {
        user.value = me
      })
      .catch(() => {
        // The server is unavailable: show the app as to a guest.
        user.value = null
      })
      .finally(() => {
        loaded.value = true
        loading = null
      })
    return loading
  }

  function setUser(value: User) {
    user.value = value
    loaded.value = true
  }

  function clear() {
    user.value = null
  }

  /** The server responded with password_change_required. */
  function requirePasswordChange() {
    if (user.value) {
      user.value.must_change_password = true
    }
  }

  /** The server responded with consents_required. */
  function requireConsents() {
    if (user.value) {
      user.value.consents_required = true
    }
  }

  return {
    user, loaded, isAuthenticated, ensureLoaded, setUser, clear, requirePasswordChange,
    requireConsents,
  }
})

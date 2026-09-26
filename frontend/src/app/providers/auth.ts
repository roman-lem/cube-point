import type { Router } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { onConsentsRequired, onPasswordChangeRequired, onUnauthorized } from '@/shared/api'

/**
 * Reaction to authorization errors from any request.
 * Lives in app: shared/api cannot know about the user store and the router.
 */
export function setupAuthHandlers(router: Router) {
  const userStore = useUserStore()

  // The session ended or was revoked (password changed on another device).
  onUnauthorized(() => {
    userStore.clear()
    const route = router.currentRoute.value
    if (route.meta.requiresAuth) {
      router.push({ name: 'login', query: { redirect: route.fullPath } })
    }
  })

  onPasswordChangeRequired(() => {
    userStore.requirePasswordChange()
    router.push({
      name: 'change-password',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  })

  onConsentsRequired(() => {
    userStore.requireConsents()
    router.push({ name: 'consent', query: { redirect: router.currentRoute.value.fullPath } })
  })
}

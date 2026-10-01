import type { Router } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { onConsentsRequired, onPasswordChangeRequired, onUnauthorized } from '@/shared/api'
import { forcedRedirect } from '../router/forcedPage'

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

  // Requests from the forced page itself and from the header get 403 too:
  // forcedRedirect does not navigate again and keeps the original page in ?redirect=.
  function goToForcedPage() {
    const target = forcedRedirect(userStore.user, router.currentRoute.value)
    if (target) {
      router.replace(target)
    }
  }

  onPasswordChangeRequired(() => {
    userStore.requirePasswordChange()
    goToForcedPage()
  })

  onConsentsRequired(() => {
    userStore.requireConsents()
    goToForcedPage()
  })
}

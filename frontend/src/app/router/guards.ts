import type { Router } from 'vue-router'
import { useUserStore } from '@/entities/user'
import { safeRedirect } from '@/shared/lib'

export function installGuards(router: Router) {
  router.beforeEach(async (to) => {
    const userStore = useUserStore()
    // The first navigation waits for /api/auth/me, after that the user is in the store.
    await userStore.ensureLoaded()
    const user = userStore.user

    // Temporary password: until it is changed, only the password change is available.
    if (user?.must_change_password && to.name !== 'change-password') {
      return { name: 'change-password', query: { redirect: to.fullPath } }
    }
    // No consents (account created by an organizer, or the text was updated): until given,
    // only the consent page and the policy and publication consent texts are available.
    if (
      user?.consents_required && !user.must_change_password &&
      !['consent', 'privacy', 'publication-consent'].includes(String(to.name))
    ) {
      return { name: 'consent', query: { redirect: to.fullPath } }
    }
    if (to.meta.requiresAuth && !user) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    // The server checks permissions; here we just do not open a page that will not load.
    if (to.meta.requiresAdmin && !user?.is_admin) {
      return { name: 'home' }
    }
    if (to.meta.guestOnly && user) {
      return safeRedirect(to.query.redirect)
    }
    return true
  })
}

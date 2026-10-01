import type { RouteLocationRaw } from 'vue-router'
import { safeRedirect } from '@/shared/lib'

// Forced pages: until the user changes the temporary password and gives the current
// consents, the app sends them there with ?redirect= to the page they were going to.
// The redirect always holds that original page, never a forced page itself
// (safeRedirect unwraps it): a request from a forced page gets 403 again,
// and the address must not nest.

/** Open while consents are missing: the texts the user agrees to. */
const CONSENT_TEXTS = ['privacy', 'publication-consent']

interface ForcedState {
  must_change_password: boolean
  consents_required: boolean
}

/** The forced page the user has to go to now, or null. The password comes first. */
export function requiredPage(user: ForcedState | null, toName: unknown) {
  if (user?.must_change_password) {
    return 'change-password'
  }
  if (user?.consents_required && !CONSENT_TEXTS.includes(String(toName))) {
    return 'consent'
  }
  return null
}

/**
 * Where to send the user instead of the route `to`, or null if `to` can be opened.
 * Already on the required forced page: null, no repeated navigation.
 */
export function forcedRedirect(
  user: ForcedState | null,
  to: { name?: unknown; fullPath: string },
): RouteLocationRaw | null {
  const page = requiredPage(user, to.name)
  if (!page || page === to.name) {
    return null
  }
  const redirect = safeRedirect(to.fullPath, '')
  return { name: page, query: redirect ? { redirect } : {} }
}

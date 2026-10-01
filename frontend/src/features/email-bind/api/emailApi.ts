import { http } from '@/shared/api'
import type { EmailState } from '@/entities/user'

/**
 * Sends a letter with a confirmation link. A new address needs the current password;
 * for the pending address the letter is sent again without it.
 */
export function requestEmail(email: string, password?: string) {
  return http.post<EmailState>('/api/auth/email', { email, password })
}

export function cancelPendingEmail() {
  return http.delete<EmailState>('/api/auth/email/pending')
}

export function removeEmail(password: string) {
  return http.post<EmailState>('/api/auth/email/remove', { password })
}

/** The link from the letter: works without logging in. */
export async function confirmEmail(token: string) {
  return (await http.post<{ email: string }>('/api/auth/email/confirm', { token })).email
}

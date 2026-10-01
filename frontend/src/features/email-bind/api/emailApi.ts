import { http } from '@/shared/api'
import type { EmailState } from '@/entities/user'

/** Sends a letter with a confirmation link; for the pending address it sends it again. */
export function requestEmail(email: string) {
  return http.post<EmailState>('/api/auth/email', { email })
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

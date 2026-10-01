import { http } from '@/shared/api'
import type { User } from '@/entities/user'

// Password reset by email, backend/app/auth/password_reset.py. Works without logging in.

/** The response is the same whether the account exists and has an email or not. */
export async function requestPasswordReset(loginOrEmail: string) {
  await http.post<unknown>('/api/auth/password-reset', { login_or_email: loginOrEmail })
}

/** Whether the link from the letter works; the account's login. */
export async function checkPasswordReset(token: string) {
  return (await http.post<{ login: string }>('/api/auth/password-reset/check', { token })).login
}

/** Sets the new password and logs in; other sessions end. */
export async function confirmPasswordReset(token: string, newPassword: string) {
  const body = { token, new_password: newPassword }
  return (await http.post<{ user: User }>('/api/auth/password-reset/confirm', body)).user
}

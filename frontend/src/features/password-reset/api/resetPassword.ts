import { http } from '@/shared/api'

/** Временный пароль участника; показывается один раз, все его сессии завершаются. */
export async function resetPassword(clubId: number, userId: number) {
  const url = `/api/clubs/${clubId}/members/${userId}/password-reset`
  return (await http.post<{ temporary_password: string }>(url)).temporary_password
}

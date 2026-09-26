import { http } from '@/shared/api'

/** A member's temporary password; shown once, all their sessions end. */
export async function resetPassword(clubId: number, userId: number) {
  const url = `/api/clubs/${clubId}/members/${userId}/password-reset`
  return (await http.post<{ temporary_password: string }>(url)).temporary_password
}

import { http } from '@/shared/api'

/**
 * A temporary password; shown once, all of the user's sessions end.
 * With clubId — by a club organizer, without — by the administrator.
 */
export async function resetPassword(userId: number, clubId?: number) {
  const url = clubId === undefined
    ? `/api/admin/users/${userId}/password-reset`
    : `/api/clubs/${clubId}/members/${userId}/password-reset`
  return (await http.post<{ temporary_password: string }>(url)).temporary_password
}

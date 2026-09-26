import { http } from '@/shared/api'

/** Deletes the club with everything in it (administrator only). The name confirms it. */
export async function deleteClub(clubId: number, name: string) {
  await http.delete<void>(`/api/admin/clubs/${clubId}`, { name })
}

import type { AdminClub } from '@/entities/club'
import { http } from '@/shared/api'

const base = (clubId: number) => `/api/admin/clubs/${clubId}/organizers`

/** Makes the user an organizer: adds them to the club or promotes a member. */
export async function addOrganizer(clubId: number, login: string) {
  return (await http.post<{ club: AdminClub }>(base(clubId), { login })).club
}

/** Demotes an organizer to a member; the last one cannot be removed. */
export async function removeOrganizer(clubId: number, userId: number) {
  return (await http.delete<{ club: AdminClub }>(`${base(clubId)}/${userId}`)).club
}

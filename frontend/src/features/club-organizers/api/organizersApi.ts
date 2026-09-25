import type { AdminClub } from '@/entities/club'
import { http } from '@/shared/api'

const base = (clubId: number) => `/api/admin/clubs/${clubId}/organizers`

/** Назначает организатором: добавляет в клуб или повышает участника. */
export async function addOrganizer(clubId: number, login: string) {
  return (await http.post<{ club: AdminClub }>(base(clubId), { login })).club
}

/** Понижает организатора до участника; последнего снять нельзя. */
export async function removeOrganizer(clubId: number, userId: number) {
  return (await http.delete<{ club: AdminClub }>(`${base(clubId)}/${userId}`)).club
}

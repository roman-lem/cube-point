import type { ClubMemberCard } from '@/entities/club'
import { http } from '@/shared/api'

const url = (clubId: number, userId: number) => `/api/clubs/${clubId}/members/${userId}/organizer`

export async function makeOrganizer(clubId: number, userId: number) {
  return (await http.put<{ member: ClubMemberCard }>(url(clubId, userId))).member
}

/** Снимает права организатора; человек остаётся в клубе. Последнего снять нельзя. */
export async function removeOrganizer(clubId: number, userId: number) {
  return (await http.delete<{ member: ClubMemberCard }>(url(clubId, userId))).member
}

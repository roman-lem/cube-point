import type { ClubMemberCard } from '@/entities/club'
import { http } from '@/shared/api'

const url = (clubId: number, userId: number) => `/api/clubs/${clubId}/members/${userId}/organizer`

export async function makeOrganizer(clubId: number, userId: number) {
  return (await http.put<{ member: ClubMemberCard }>(url(clubId, userId))).member
}

/** Removes organizer rights; the person stays in the club. The last one cannot be removed. */
export async function removeOrganizer(clubId: number, userId: number) {
  return (await http.delete<{ member: ClubMemberCard }>(url(clubId, userId))).member
}

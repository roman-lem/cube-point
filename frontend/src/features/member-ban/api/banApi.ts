import type { ClubMemberCard } from '@/entities/club'
import { http } from '@/shared/api'

const url = (clubId: number, userId: number) => `/api/clubs/${clubId}/members/${userId}/ban`

export async function banMember(clubId: number, userId: number, reason: string) {
  return (await http.put<{ member: ClubMemberCard }>(url(clubId, userId), { reason })).member
}

export async function unbanMember(clubId: number, userId: number) {
  return (await http.delete<{ member: ClubMemberCard }>(url(clubId, userId))).member
}

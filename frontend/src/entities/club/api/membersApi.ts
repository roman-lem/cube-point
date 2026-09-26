import { http } from '@/shared/api'
import type { ClubMemberCard, ClubMembersList, MemberFilter } from '../model/types'

/** Club members with search by name (and by login for organizers); the filter is for organizers only. */
export function fetchMembers(clubId: number, query = '', filter: MemberFilter = 'all') {
  const params = new URLSearchParams({ q: query, filter })
  return http.get<ClubMembersList>(`/api/clubs/${clubId}/members?${params}`)
}

/** Member card for the organizer: meetups with results, role, ban. */
export async function fetchMemberCard(clubId: number, userId: number) {
  return (await http.get<{ member: ClubMemberCard }>(`/api/clubs/${clubId}/members/${userId}`)).member
}

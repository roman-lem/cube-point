import { http } from '@/shared/api'
import type { ClubMemberCard, ClubMembersList, MemberFilter } from '../model/types'

/** Участники клуба с поиском по имени (организатору — и по логину); фильтр — только у организатора. */
export function fetchMembers(clubId: number, query = '', filter: MemberFilter = 'all') {
  const params = new URLSearchParams({ q: query, filter })
  return http.get<ClubMembersList>(`/api/clubs/${clubId}/members?${params}`)
}

/** Карточка участника для организатора: встречи с результатами, роль, блокировка. */
export async function fetchMemberCard(clubId: number, userId: number) {
  return (await http.get<{ member: ClubMemberCard }>(`/api/clubs/${clubId}/members/${userId}`)).member
}

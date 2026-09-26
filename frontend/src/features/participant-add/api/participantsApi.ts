import type { RequestStatus } from '@/entities/meetup'
import { http } from '@/shared/api'

export interface Candidate {
  user: { id: number; display_name: string; login: string }
  /** Status of the request for this meetup; null means no request. */
  status: RequestStatus | null
}

export interface AddedParticipant {
  user: { id: number; display_name: string; login: string }
  /** Only for a new account: shown once. */
  temporary_password: string | null
}

const base = (meetupId: number) => `/api/meetups/${meetupId}`

/** Club members (except banned ones) with search by name and login. */
export async function fetchCandidates(meetupId: number, query: string) {
  const url = `${base(meetupId)}/candidates?q=${encodeURIComponent(query)}`
  return (await http.get<{ candidates: Candidate[] }>(url)).candidates
}

export function addMember(meetupId: number, userId: number) {
  return http.post<AddedParticipant>(`${base(meetupId)}/participants`, { user_id: userId })
}

/** A new account with a temporary password, approved for the meetup right away. */
export function addNewcomer(meetupId: number, displayName: string, login: string) {
  return http.post<AddedParticipant>(`${base(meetupId)}/participants`, {
    display_name: displayName,
    login,
  })
}

/** A new account with a temporary password, added to the club right away (from the club member list). */
export function createClubMember(clubId: number, displayName: string, login: string) {
  return http.post<AddedParticipant>(`/api/clubs/${clubId}/members`, {
    display_name: displayName,
    login,
  })
}

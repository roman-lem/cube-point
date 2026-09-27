import { http } from '@/shared/api'
import type { ClubPageData, ClubSummary } from '../model/types'

export async function fetchClubs() {
  return (await http.get<{ clubs: ClubSummary[] }>('/api/clubs')).clubs
}

/**
 * Where the site root leads a logged-in user: the last club they opened (lastId)
 * if they are still a member there, otherwise the club of their latest meetup, or null.
 */
export async function fetchHomeClubId(lastId: number | null) {
  const query = lastId ? `?last=${lastId}` : ''
  return (await http.get<{ club_id: number | null }>(`/api/auth/home-club${query}`)).club_id
}

export function fetchClub(clubId: number) {
  return http.get<ClubPageData>(`/api/clubs/${clubId}`)
}

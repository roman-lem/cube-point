import { http } from '@/shared/api'
import type { ClubPageData, ClubSummary } from '../model/types'

export async function fetchClubs() {
  return (await http.get<{ clubs: ClubSummary[] }>('/api/clubs')).clubs
}

/** Клуб последней встречи вошедшего (куда ведёт корень сайта) или null. */
export async function fetchHomeClubId() {
  return (await http.get<{ club_id: number | null }>('/api/auth/home-club')).club_id
}

export function fetchClub(clubId: number) {
  return http.get<ClubPageData>(`/api/clubs/${clubId}`)
}

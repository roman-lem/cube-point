import { http } from '@/shared/api'
import type { ClubPageData, ClubSummary } from '../model/types'

export async function fetchClubs() {
  return (await http.get<{ clubs: ClubSummary[] }>('/api/clubs')).clubs
}

export function fetchClub(clubId: number) {
  return http.get<ClubPageData>(`/api/clubs/${clubId}`)
}

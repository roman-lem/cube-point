import { http } from '@/shared/api'
import type { AdminClub, AdminClubSummary } from '../model/types'

// Только для администратора, см. backend/app/admin.py.

export async function fetchAdminClubs() {
  return (await http.get<{ clubs: AdminClubSummary[] }>('/api/admin/clubs')).clubs
}

export async function fetchAdminClub(clubId: number) {
  return (await http.get<{ club: AdminClub }>(`/api/admin/clubs/${clubId}`)).club
}

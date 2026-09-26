import type { AdminClub, UserRef } from '@/entities/club'
import { http } from '@/shared/api'

export interface NewClub {
  name: string
  city: string
  timezone: string
  /** Login of the first organizer: a club is not created without one. */
  organizer_login: string
}

export async function createClub(data: NewClub) {
  return (await http.post<{ club: AdminClub }>('/api/admin/clubs', data)).club
}

/** Users whose login contains query (up to 10). */
export async function searchUsers(query: string) {
  const url = `/api/admin/users?q=${encodeURIComponent(query)}`
  return (await http.get<{ users: UserRef[] }>(url)).users
}

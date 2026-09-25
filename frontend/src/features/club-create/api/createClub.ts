import type { AdminClub, UserRef } from '@/entities/club'
import { http } from '@/shared/api'

export interface NewClub {
  name: string
  city: string
  timezone: string
  /** Логин первого организатора: без него клуб не создаётся. */
  organizer_login: string
}

export async function createClub(data: NewClub) {
  return (await http.post<{ club: AdminClub }>('/api/admin/clubs', data)).club
}

/** Пользователи, у которых логин содержит query (до 10). */
export async function searchUsers(query: string) {
  const url = `/api/admin/users?q=${encodeURIComponent(query)}`
  return (await http.get<{ users: UserRef[] }>(url)).users
}

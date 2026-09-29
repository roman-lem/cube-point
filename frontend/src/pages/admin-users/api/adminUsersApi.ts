import type { ClubRole, MemberMeetup, Restriction } from '@/entities/club'
import { http } from '@/shared/api'

// Administrator only, see backend/app/admin.py.

export type UserFilter = 'all' | 'admins' | 'organizers' | 'deleted'

/** A row of the user list. The email is only in administrator responses. */
export interface AdminUser {
  id: number
  display_name: string
  /** null for a deleted account. */
  login: string | null
  email: string | null
  created_at: string
  deleted_at: string | null
  is_admin: boolean
  /** A deleted account that kept its name in results and records. */
  kept_name: boolean
  clubs: { id: number; name: string; role: ClubRole; banned: boolean }[]
}

/** The latest consent of a type. */
export interface ConsentEntry {
  version: string
  accepted_at: string
}

export interface AdminUserCard extends AdminUser {
  consents: Partial<Record<'processing' | 'publication' | 'age' | 'deleted_name', ConsentEntry>>
  /** Meetups with the user's results in all clubs, newest first. */
  meetups: (MemberMeetup & { club: { id: number; name: string } })[]
  restrictions: { reset_password: Restriction }
}

export async function fetchAdminUsers(query: string, filter: UserFilter, offset: number) {
  const params = new URLSearchParams({ q: query, filter, offset: String(offset) })
  return http.get<{ users: AdminUser[]; has_more: boolean }>(`/api/admin/users?${params}`)
}

export async function fetchAdminUser(userId: number) {
  return (await http.get<{ user: AdminUserCard }>(`/api/admin/users/${userId}`)).user
}

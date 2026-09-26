import { http } from '@/shared/api'

// Administrator only, see backend/app/admin.py.

/** A deleted account that kept its name in results and records. */
export interface DeletedUser {
  id: number
  display_name: string
  deleted_at: string
  /** Version of the publication consent that is not withdrawn for the name. */
  consent_version: string
}

/** Deleted accounts that kept their name; query is part of the name. */
export async function searchDeletedUsers(query: string) {
  const params = new URLSearchParams({ q: query })
  return (await http.get<{ users: DeletedUser[] }>(`/api/admin/deleted-users?${params}`)).users
}

/** Withdraws the consent: the name is replaced with the deleted-user name. */
export async function anonymizeDeletedUser(userId: number) {
  await http.post<void>(`/api/admin/deleted-users/${userId}/anonymize`)
}

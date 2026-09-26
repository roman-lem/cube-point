import { http } from '@/shared/api'

// Только для администратора, см. backend/app/admin.py.

/** Удалённый аккаунт, оставивший имя в результатах и рекордах. */
export interface DeletedUser {
  id: number
  display_name: string
  deleted_at: string
  /** Версия согласия на распространение, которое не отозвано для имени. */
  consent_version: string
}

/** Удалённые аккаунты с сохранённым именем; query — часть имени. */
export async function searchDeletedUsers(query: string) {
  const params = new URLSearchParams({ q: query })
  return (await http.get<{ users: DeletedUser[] }>(`/api/admin/deleted-users?${params}`)).users
}

/** Отзыв согласия: имя заменяется на «Удалённый участник». */
export async function anonymizeDeletedUser(userId: number) {
  await http.post<void>(`/api/admin/deleted-users/${userId}/anonymize`)
}

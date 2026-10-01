import { http } from '@/shared/api'
import type { User } from '@/entities/user'

/** The user's own name change, at most once in 30 days (backend/app/names.py). */
export async function changeDisplayName(displayName: string) {
  return (await http.post<{ user: User }>('/api/auth/display-name', { display_name: displayName })).user
}

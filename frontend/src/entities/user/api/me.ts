import { http } from '@/shared/api'
import type { User } from '../model/types'

/** Текущий пользователь или null для гостя. */
export async function fetchMe(): Promise<User | null> {
  const data = await http.get<{ user: User | null }>('/api/auth/me')
  return data.user
}

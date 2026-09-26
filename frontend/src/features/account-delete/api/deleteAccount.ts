import { http } from '@/shared/api'

/** keepName — оставить имя в результатах и рекордах (без отзыва согласия на распространение). */
export async function deleteAccount(password: string, keepName: boolean) {
  await http.post<void>('/api/auth/delete-account', { password, keep_name: keepName })
}

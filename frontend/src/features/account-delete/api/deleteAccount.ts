import { http } from '@/shared/api'

export async function deleteAccount(password: string) {
  await http.post<void>('/api/auth/delete-account', { password })
}

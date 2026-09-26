import { http } from '@/shared/api'

/** keepName: keep the name in results and records (without withdrawing the publication consent). */
export async function deleteAccount(password: string, keepName: boolean) {
  await http.post<void>('/api/auth/delete-account', { password, keep_name: keepName })
}

import { http } from '@/shared/api'
import type { User } from '@/entities/user'

interface UserResponse {
  user: User
}

export async function login(data: { login: string; password: string; remember: boolean }) {
  return (await http.post<UserResponse>('/api/auth/login', data)).user
}

export async function register(data: { display_name: string; login: string; password: string }) {
  return (await http.post<UserResponse>('/api/auth/register', data)).user
}

export async function logout() {
  await http.post<void>('/api/auth/logout')
}

/** current_password не нужен, если пароль меняется принудительно (временный пароль). */
export async function changePassword(data: { current_password?: string; new_password: string }) {
  return (await http.post<UserResponse>('/api/auth/password', data)).user
}

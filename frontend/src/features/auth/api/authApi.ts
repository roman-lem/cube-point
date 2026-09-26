import { http } from '@/shared/api'
import type { User } from '@/entities/user'
import { consentsPayload, type ConsentChoice } from '../model/consents'

interface UserResponse {
  user: User
}

export async function login(data: { login: string; password: string; remember: boolean }) {
  return (await http.post<UserResponse>('/api/auth/login', data)).user
}

export async function register(data: {
  display_name: string
  login: string
  password: string
  consents: ConsentChoice
}) {
  const body = { ...data, consents: consentsPayload(data.consents) }
  return (await http.post<UserResponse>('/api/auth/register', body)).user
}

/** Whether registration is open (closed by the REGISTRATION_OPEN environment variable). */
export async function fetchRegistrationOpen() {
  return (await http.get<{ open: boolean }>('/api/auth/registration')).open
}

export async function acceptConsents(consents: ConsentChoice) {
  const body = { consents: consentsPayload(consents) }
  return (await http.post<UserResponse>('/api/auth/consents', body)).user
}

export async function logout() {
  await http.post<void>('/api/auth/logout')
}

/** current_password is not needed if the password change is forced (temporary password). */
export async function changePassword(data: { current_password?: string; new_password: string }) {
  return (await http.post<UserResponse>('/api/auth/password', data)).user
}

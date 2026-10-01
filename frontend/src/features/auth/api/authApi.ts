import { http } from '@/shared/api'
import type { User } from '@/entities/user'
import { consentsPayload, type ConsentChoice } from '../model/consents'

interface UserResponse {
  user: User
}

export async function login(data: { login: string; password: string; remember: boolean }) {
  return (await http.post<UserResponse>('/api/auth/login', data)).user
}

/**
 * form_token and website are the protection from scripts: the token from
 * fetchRegistration (the server checks how long the form was filled) and
 * the hidden trap field that people leave empty.
 */
export async function register(data: {
  display_name: string
  login: string
  password: string
  consents: ConsentChoice
  form_token: string
  website: string
}) {
  const body = { ...data, consents: consentsPayload(data.consents) }
  return (await http.post<UserResponse>('/api/auth/register', body)).user
}

/** Whether registration is open (REGISTRATION_OPEN) and the token of the form. */
export function fetchRegistration() {
  return http.get<{ open: boolean; form_token: string }>('/api/auth/registration')
}

export async function acceptConsents(consents: ConsentChoice) {
  const body = { consents: consentsPayload(consents) }
  return (await http.post<UserResponse>('/api/auth/consents', body)).user
}

export async function logout() {
  await http.post<void>('/api/auth/logout')
}

/** Ends all sessions of the account, the current one too. */
export async function logoutEverywhere() {
  await http.post<void>('/api/auth/logout-everywhere')
}

/** current_password is not needed if the password change is forced (temporary password). */
export async function changePassword(data: { current_password?: string; new_password: string }) {
  return (await http.post<UserResponse>('/api/auth/password', data)).user
}

import type { RequestStatus } from '@/entities/meetup'
import { http } from '@/shared/api'

export interface Candidate {
  user: { id: number; display_name: string; login: string }
  /** Статус заявки на эту встречу; null — заявки нет. */
  status: RequestStatus | null
}

export interface AddedParticipant {
  user: { id: number; display_name: string; login: string }
  /** Только у нового аккаунта: показывается один раз. */
  temporary_password: string | null
}

const base = (meetupId: number) => `/api/meetups/${meetupId}`

/** Участники клуба (кроме заблокированных) с поиском по имени и логину. */
export async function fetchCandidates(meetupId: number, query: string) {
  const url = `${base(meetupId)}/candidates?q=${encodeURIComponent(query)}`
  return (await http.get<{ candidates: Candidate[] }>(url)).candidates
}

export function addMember(meetupId: number, userId: number) {
  return http.post<AddedParticipant>(`${base(meetupId)}/participants`, { user_id: userId })
}

/** Новый аккаунт с временным паролем, сразу подтверждённый на встрече. */
export function addNewcomer(meetupId: number, displayName: string, login: string) {
  return http.post<AddedParticipant>(`${base(meetupId)}/participants`, {
    display_name: displayName,
    login,
  })
}

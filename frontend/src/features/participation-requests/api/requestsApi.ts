import type { RequestStatus } from '@/entities/meetup'
import { http } from '@/shared/api'

export interface ParticipationRequest {
  user: { id: number; display_name: string; login: string | null }
  status: RequestStatus
  requested_at: string
  decided_at: string | null
}

const base = (meetupId: number) => `/api/meetups/${meetupId}/requests`

/** Все заявки встречи, ожидающие — первыми. */
export async function fetchRequests(meetupId: number) {
  return (await http.get<{ requests: ParticipationRequest[] }>(base(meetupId))).requests
}

export async function approveRequest(meetupId: number, userId: number) {
  const url = `${base(meetupId)}/${userId}/approve`
  return (await http.post<{ request: ParticipationRequest }>(url)).request
}

export async function rejectRequest(meetupId: number, userId: number) {
  const url = `${base(meetupId)}/${userId}/reject`
  return (await http.post<{ request: ParticipationRequest }>(url)).request
}

/** Подтверждает все ожидающие заявки, кроме заблокированных в клубе. */
export async function approveAll(meetupId: number) {
  return (await http.post<{ approved: number }>(`${base(meetupId)}/approve-all`)).approved
}

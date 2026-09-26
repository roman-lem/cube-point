import type { RequestStatus } from '@/entities/meetup'
import { http } from '@/shared/api'

/**
 * A participation request via an invitation link. If a request already exists,
 * the server returns its status and does not create a new one.
 */
export function joinMeetup(token: string) {
  return http.post<{ meetup_id: number; status: RequestStatus }>(
    `/api/join/${encodeURIComponent(token)}`,
  )
}

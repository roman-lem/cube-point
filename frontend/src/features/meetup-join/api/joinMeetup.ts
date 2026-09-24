import type { RequestStatus } from '@/entities/meetup'
import { http } from '@/shared/api'

/**
 * Заявка на участие по ссылке-приглашению. Если заявка уже есть,
 * сервер возвращает её статус, новую не создаёт.
 */
export function joinMeetup(token: string) {
  return http.post<{ meetup_id: number; status: RequestStatus }>(
    `/api/join/${encodeURIComponent(token)}`,
  )
}

import type { DeskEvent } from '@/entities/meetup'
import { http } from '@/shared/api'
import type { Attempt } from '@/shared/lib'

const attemptUrl = (meetupId: number, eventId: string, userId: number, number: number) =>
  `/api/meetups/${meetupId}/events/${encodeURIComponent(eventId)}` +
  `/participants/${userId}/attempts/${number}`

/**
 * Ввод или правка попытки организатором. version — версия серии, прочитанная
 * клиентом (null — серии ещё нет). Ответ и ошибка конфликта (в ApiError.data.event)
 * содержат свежие данные всей дисциплины.
 */
export async function saveAttempt(
  meetupId: number,
  eventId: string,
  userId: number,
  number: number,
  attempt: Attempt,
  version: number | null,
) {
  const url = attemptUrl(meetupId, eventId, userId, number)
  return (await http.put<{ event: DeskEvent }>(url, { ...attempt, version })).event
}

/**
 * Стирает ошибочно введённую попытку — только последнюю в серии.
 * Серия без попыток удаляется. Ответ — свежие данные дисциплины.
 */
export async function deleteAttempt(
  meetupId: number,
  eventId: string,
  userId: number,
  number: number,
  version: number | null,
) {
  const url = attemptUrl(meetupId, eventId, userId, number)
  return (await http.delete<{ event: DeskEvent }>(url, { version })).event
}

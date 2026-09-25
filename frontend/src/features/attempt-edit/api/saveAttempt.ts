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

/** Запись журнала попытки: значение, кто и когда его установил (ISO в UTC). */
export interface AttemptHistoryEntry extends Attempt {
  solution: string | null
  /** null — аккаунт удалён. */
  changed_by: { id: number; display_name: string } | null
  changed_at: string
}

/** Журнал попытки по порядку, первая запись — исходный результат. */
export async function fetchAttemptHistory(
  meetupId: number,
  eventId: string,
  userId: number,
  number: number,
) {
  const url = `${attemptUrl(meetupId, eventId, userId, number)}/history`
  return (await http.get<{ history: AttemptHistoryEntry[] }>(url)).history
}

/** Возвращает попытке исходный результат — обычная правка, тоже попадает в журнал. */
export async function restoreAttempt(
  meetupId: number,
  eventId: string,
  userId: number,
  number: number,
  version: number | null,
) {
  const url = `${attemptUrl(meetupId, eventId, userId, number)}/restore`
  return (await http.post<{ event: DeskEvent }>(url, { version })).event
}

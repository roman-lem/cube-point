import type { DeskEvent } from '@/entities/meetup'
import { http } from '@/shared/api'
import type { Attempt } from '@/shared/lib'

const attemptUrl = (meetupId: number, eventId: string, userId: number, number: number) =>
  `/api/meetups/${meetupId}/events/${encodeURIComponent(eventId)}` +
  `/participants/${userId}/attempts/${number}`

/**
 * An organizer enters or edits an attempt. version is the series version read
 * by the client (null: no series yet). The response and the conflict error (in ApiError.data.event)
 * contain fresh data for the whole event.
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
 * Erases an attempt entered by mistake, only the last one in the series.
 * A series without attempts is deleted. The response is fresh event data.
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

/** An attempt history entry: the value, who set it and when (ISO in UTC). */
export interface AttemptHistoryEntry extends Attempt {
  solution: string | null
  /** null means the account is deleted. */
  changed_by: { id: number; display_name: string } | null
  changed_at: string
}

/** Attempt history in order, the first entry is the original result. */
export async function fetchAttemptHistory(
  meetupId: number,
  eventId: string,
  userId: number,
  number: number,
) {
  const url = `${attemptUrl(meetupId, eventId, userId, number)}/history`
  return (await http.get<{ history: AttemptHistoryEntry[] }>(url)).history
}

/** Restores the attempt's original result: a regular edit that also goes to the history. */
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

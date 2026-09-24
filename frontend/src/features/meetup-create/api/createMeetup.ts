import type { Meetup } from '@/entities/meetup'
import { http } from '@/shared/api'
import type { SeriesFormat } from '@/shared/lib'

export interface CreateMeetupData {
  /** Дата и время — по часам клуба: "2026-10-19", "18:00". */
  date: string
  starts_at: string
  ends_at: string
  place: string
  address: string
  events: { event_id: string; format: SeriesFormat; scrambles: string[] }[]
}

export async function createMeetup(clubId: number, data: CreateMeetupData) {
  return (await http.post<{ meetup: Meetup }>(`/api/clubs/${clubId}/meetups`, data)).meetup
}

import { http } from '@/shared/api'
import type { MeetupDesk, PrintEvent } from '../model/desk'
import type { ActiveMeetup, JoinPreview, MeetupPageData, MeetupSummary } from '../model/types'

export async function fetchClubMeetups(clubId: number) {
  return (await http.get<{ meetups: MeetupSummary[] }>(`/api/clubs/${clubId}/meetups`)).meetups
}

export function fetchMeetup(meetupId: number) {
  return http.get<MeetupPageData>(`/api/meetups/${meetupId}`)
}

export async function fetchJoinPreview(token: string) {
  const path = `/api/join/${encodeURIComponent(token)}`
  return (await http.get<{ meetup: JoinPreview }>(path)).meetup
}

/** Идущие встречи, где текущий пользователь подтверждён, с его сериями. */
export async function fetchActiveMeetups() {
  return (await http.get<{ meetups: ActiveMeetup[] }>('/api/me/active')).meetups
}

/** Панель встречи организатора: участники и таблицы ввода по дисциплинам. */
export function fetchDesk(meetupId: number) {
  return http.get<MeetupDesk>(`/api/meetups/${meetupId}/desk`)
}

/** Скрамблы встречи для бланков. FMC сервер не отдаёт. */
export async function fetchPrintScrambles(meetupId: number) {
  return (await http.get<{ events: PrintEvent[] }>(`/api/meetups/${meetupId}/scrambles`)).events
}

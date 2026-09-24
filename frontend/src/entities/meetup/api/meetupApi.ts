import { http } from '@/shared/api'
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

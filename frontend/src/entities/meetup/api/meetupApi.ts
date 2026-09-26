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

/** Live meetups where the current user is approved, with their series. */
export async function fetchActiveMeetups() {
  return (await http.get<{ meetups: ActiveMeetup[] }>('/api/me/active')).meetups
}

/** Organizer's meetup desk: participants and entry tables per event. */
export function fetchDesk(meetupId: number) {
  return http.get<MeetupDesk>(`/api/meetups/${meetupId}/desk`)
}

/** Meetup scrambles for score sheets. The server does not return FMC. */
export async function fetchPrintScrambles(meetupId: number) {
  return (await http.get<{ events: PrintEvent[] }>(`/api/meetups/${meetupId}/scrambles`)).events
}

import { ApiError, http } from '@/shared/api'
import type { EventResults, LiveSeriesMeetup, MySeries } from '../model/types'

const eventPath = (meetupId: number, eventId: string) =>
  `/api/meetups/${meetupId}/events/${encodeURIComponent(eventId)}`

/** One's own series in a meetup event, or null if it is not started. */
export async function fetchMySeries(meetupId: number, eventId: string): Promise<MySeries | null> {
  try {
    return (await http.get<{ series: MySeries }>(`${eventPath(meetupId, eventId)}/series/me`))
      .series
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      return null
    }
    throw e
  }
}

export function fetchEventResults(meetupId: number, eventId: string) {
  return http.get<EventResults>(`${eventPath(meetupId, eventId)}/results`)
}

/** One's own series at live meetups: for the "Statistics" tab. */
export async function fetchLiveSeries(): Promise<LiveSeriesMeetup[]> {
  return (await http.get<{ meetups: LiveSeriesMeetup[] }>('/api/me/series')).meetups
}

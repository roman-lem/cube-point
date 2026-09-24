import { ApiError, http } from '@/shared/api'
import type { EventResults, LiveSeriesMeetup, MySeries } from '../model/types'

const eventPath = (meetupId: number, eventId: string) =>
  `/api/meetups/${meetupId}/events/${encodeURIComponent(eventId)}`

/** Своя серия в дисциплине встречи или null, если она не начата. */
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

/** Свои серии на идущих встречах: для вкладки «Статистика». */
export async function fetchLiveSeries(): Promise<LiveSeriesMeetup[]> {
  return (await http.get<{ meetups: LiveSeriesMeetup[] }>('/api/me/series')).meetups
}

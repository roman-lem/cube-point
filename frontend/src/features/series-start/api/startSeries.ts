import { fetchMySeries, type MySeries } from '@/entities/series'
import { ApiError, http } from '@/shared/api'

/** Starts a series. If it is already started (double tap), returns it. */
export async function startSeries(meetupId: number, eventId: string): Promise<MySeries> {
  const path = `/api/meetups/${meetupId}/events/${encodeURIComponent(eventId)}/series`
  try {
    return (await http.post<{ series: MySeries }>(path)).series
  } catch (e) {
    if (e instanceof ApiError && e.code === 'series_exists') {
      const series = await fetchMySeries(meetupId, eventId)
      if (series) {
        return series
      }
    }
    throw e
  }
}

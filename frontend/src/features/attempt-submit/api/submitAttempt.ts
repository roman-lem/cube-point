import { fetchMySeries, type MySeries } from '@/entities/series'
import { ApiError, http } from '@/shared/api'
import type { Penalty } from '@/shared/lib'

export interface AttemptResult {
  /** Time without the penalty in hundredths of a second; DNF may have none. */
  value: number | null
  penalty: Exclude<Penalty, 'dns'>
}

/**
 * Saves the next attempt of the series.
 *
 * If the series has been changed (another tab, the organizer) or the attempt is already
 * saved, reloads the series and returns it with conflict: true,
 * so the attempt can be saved again on top of the fresh data.
 */
export async function submitAttempt(
  series: MySeries,
  result: AttemptResult,
): Promise<{ series: MySeries; conflict: boolean }> {
  try {
    const response = await http.post<{ series: MySeries }>(`/api/series/${series.id}/attempts`, {
      attempt_number: series.next_attempt?.number,
      value: result.value,
      penalty: result.penalty,
      version: series.version,
    })
    return { series: response.series, conflict: false }
  } catch (e) {
    if (
      e instanceof ApiError &&
      (e.code === 'version_conflict' || e.code === 'wrong_attempt_number')
    ) {
      const fresh = await fetchMySeries(series.meetup_id, series.event_id)
      if (fresh) {
        return { series: fresh, conflict: true }
      }
    }
    throw e
  }
}

import { fetchMySeries, type MySeries } from '@/entities/series'
import { ApiError, http } from '@/shared/api'
import type { Penalty } from '@/shared/lib'

export interface AttemptResult {
  /** Время без штрафа в сотых долях секунды; у DNF может не быть. */
  value: number | null
  penalty: Exclude<Penalty, 'dns'>
}

/**
 * Сохраняет следующую попытку серии.
 *
 * Если серию успели изменить (другая вкладка, организатор) или попытка уже
 * сохранена, перечитывает серию и возвращает её с conflict: true —
 * тогда попытку можно сохранить заново поверх свежих данных.
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

import { fetchMySeries, type MySeries } from '@/entities/series'
import { ApiError, http } from '@/shared/api'
import type { FmcCheck } from '@/shared/lib'

// Попытка FMC на сервере: старт, черновик, заморозка и сдача.
// Правила — раздел «FMC» в CLAUDE.md, адреса — backend/app/fmc.py.

const fmcPath = (series: MySeries, action: string) => `/api/series/${series.id}/fmc/${action}`
const attemptNumber = (series: MySeries) => series.next_attempt?.number

/** Старт попытки: сервер фиксирует время старта и отдаёт скрамбл. */
export async function startFmcAttempt(series: MySeries): Promise<MySeries> {
  const response = await http.post<{ series: MySeries }>(fmcPath(series, 'start'), {
    attempt_number: attemptNumber(series),
  })
  return response.series
}

export async function saveFmcDraft(series: MySeries, solution: string): Promise<void> {
  await http.put(fmcPath(series, 'draft'), { attempt_number: attemptNumber(series), solution })
}

/**
 * Первый шаг сдачи: замораживает решение и время сдачи. Если время уже
 * вышло, сервер сразу сохраняет попытку как DNF с этим решением.
 */
export async function freezeFmcSolution(series: MySeries, solution: string): Promise<MySeries> {
  const response = await http.post<{ series: MySeries }>(fmcPath(series, 'freeze'), {
    attempt_number: attemptNumber(series),
    solution,
  })
  return response.series
}

/** «Вернуться к решению»: снимает заморозку. */
export async function unfreezeFmcSolution(series: MySeries): Promise<MySeries> {
  const response = await http.delete<{ series: MySeries }>(fmcPath(series, 'freeze'), {
    attempt_number: attemptNumber(series),
  })
  return response.series
}

/**
 * Второй шаг сдачи: результат проверки решения solution.
 *
 * Если серия или решение успели измениться, перечитывает серию и возвращает
 * её с conflict: true — решение нужно проверить заново.
 */
export async function submitFmcResult(
  series: MySeries,
  solution: string,
  check: FmcCheck,
): Promise<{ series: MySeries; conflict: boolean }> {
  try {
    const response = await http.post<{ series: MySeries }>(fmcPath(series, 'result'), {
      attempt_number: attemptNumber(series),
      solution,
      version: series.version,
      ...('moves' in check ? { value: check.moves, penalty: 'none' } : { value: null, penalty: 'dnf' }),
    })
    return { series: response.series, conflict: false }
  } catch (e) {
    if (
      e instanceof ApiError &&
      ['version_conflict', 'wrong_attempt_number', 'solution_changed'].includes(e.code)
    ) {
      const fresh = await fetchMySeries(series.meetup_id, series.event_id)
      if (fresh) {
        return { series: fresh, conflict: true }
      }
    }
    throw e
  }
}

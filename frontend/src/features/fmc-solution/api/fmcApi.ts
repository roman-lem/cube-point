import { fetchMySeries, type MySeries } from '@/entities/series'
import { ApiError, http } from '@/shared/api'
import type { FmcCheck } from '@/shared/lib'

// FMC attempt on the server: start, draft, freeze and submission.
// Rules: "FMC" in docs/ARCHITECTURE.md, routes: backend/app/fmc.py.

const fmcPath = (series: MySeries, action: string) => `/api/series/${series.id}/fmc/${action}`
const attemptNumber = (series: MySeries) => series.next_attempt?.number

/** Attempt start: the server records the start time and returns the scramble. */
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
 * First submission step: freezes the solution and the submission time. If time has already
 * run out, the server saves the attempt as DNF with this solution right away.
 */
export async function freezeFmcSolution(series: MySeries, solution: string): Promise<MySeries> {
  const response = await http.post<{ series: MySeries }>(fmcPath(series, 'freeze'), {
    attempt_number: attemptNumber(series),
    solution,
  })
  return response.series
}

/** "Back to solution": removes the freeze. */
export async function unfreezeFmcSolution(series: MySeries): Promise<MySeries> {
  const response = await http.delete<{ series: MySeries }>(fmcPath(series, 'freeze'), {
    attempt_number: attemptNumber(series),
  })
  return response.series
}

/**
 * Second submission step: the result of checking the solution.
 *
 * If the series or the solution has changed, reloads the series and returns
 * it with conflict: true; the solution has to be checked again.
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

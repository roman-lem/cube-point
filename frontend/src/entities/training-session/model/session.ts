// Training session: solves of one event, stored only in the browser.
// Rules: "Timer" in docs/ARCHITECTURE.md. Pure functions without Vue: parsing
// stored data, session changes and statistics.
import { DNF, attemptValue, averageOf } from '@/shared/lib'

/** Training has no DNS: only meetup finish sets it. */
export type TrainingPenalty = 'none' | 'plus2' | 'dnf'

export interface TrainingSolve {
  /** Time without the penalty in hundredths of a second. */
  value: number
  penalty: TrainingPenalty
  /** Solve moment (ms since 1970), also the solve's ID in the session. */
  at: number
}

export interface SessionStats {
  ao5: number | null
  ao12: number | null
  /** Best solve, DNF if all are DNF, or null if there are no solves. */
  best: number | null
  count: number
}

/** Storage format version. Data of another version is not read. */
export const SESSION_VERSION = 1

const PENALTIES: TrainingPenalty[] = ['none', 'plus2', 'dnf']

/**
 * Solves from a storage string. Never throws:
 * broken data or another version gives an empty session, an invalid
 * solve (or a repeated at) is dropped, the rest are kept.
 */
export function parseSession(raw: string | null): TrainingSolve[] {
  if (!raw) {
    return []
  }
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return []
  }
  if (!isObject(data) || data.version !== SESSION_VERSION || !Array.isArray(data.solves)) {
    return []
  }
  const seen = new Set<number>()
  const solves: TrainingSolve[] = []
  for (const item of data.solves) {
    if (isSolve(item) && !seen.has(item.at)) {
      seen.add(item.at)
      solves.push({ value: item.value, penalty: item.penalty, at: item.at })
    }
  }
  return solves
}

export function serializeSession(solves: TrainingSolve[]): string {
  return JSON.stringify({ version: SESSION_VERSION, solves })
}

/** A new solve at the end of the session. at is always greater than the previous one. */
export function addSolve(
  solves: TrainingSolve[],
  value: number,
  penalty: TrainingPenalty,
  now = Date.now(),
): TrainingSolve[] {
  const last = solves[solves.length - 1]
  const at = last && last.at >= now ? last.at + 1 : now
  return [...solves, { value, penalty, at }]
}

export function setPenalty(
  solves: TrainingSolve[],
  at: number,
  penalty: TrainingPenalty,
): TrainingSolve[] {
  return solves.map((s) => (s.at === at ? { ...s, penalty } : s))
}

export function removeSolve(solves: TrainingSolve[], at: number): TrainingSolve[] {
  return solves.filter((s) => s.at !== at)
}

export function sessionStats(solves: TrainingSolve[]): SessionStats {
  const values = solves.map((s) => attemptValue(s, 'time'))
  const successful = values.filter((v) => v !== DNF)
  let best: number | null = null
  if (successful.length > 0) {
    best = Math.min(...successful)
  } else if (values.length > 0) {
    best = DNF
  }
  return {
    ao5: averageOf(solves, 5, 'time'),
    ao12: averageOf(solves, 12, 'time'),
    best,
    count: solves.length,
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isSolve(item: unknown): item is TrainingSolve {
  return (
    isObject(item) &&
    Number.isInteger(item.value) &&
    (item.value as number) > 0 &&
    PENALTIES.includes(item.penalty as TrainingPenalty) &&
    Number.isInteger(item.at)
  )
}

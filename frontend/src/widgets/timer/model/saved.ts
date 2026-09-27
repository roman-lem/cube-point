// Timer state in sessionStorage: survives a reload and a tab unloaded by the browser.
// Pure functions without Vue. Time in the state is ms since 1970 (timerNow),
// so the saved start moments are valid after a reload.
import { transition, type Phase, type TimerState } from './machine'

/** Storage format version. Data of another version is not read. */
export const SAVED_VERSION = 1

export interface SavedTimer {
  /** Whose solve: `training:<event_id>` or `series:<series_id>:<attempt>`. */
  owner: string
  state: TimerState
}

const PHASES: Phase[] = ['idle', 'inspection', 'holding', 'ready', 'running', 'stopped']
const PENALTIES = ['none', 'plus2', 'dnf']

/**
 * Time for the machine: ms since 1970, as precise and monotonic as performance.now()
 * within the page, and comparable with moments saved before a reload.
 */
export function timerNow(): number {
  return performance.timeOrigin + performance.now()
}

/**
 * The saved timer. Never throws: broken data or another version gives null.
 * Holding does not survive a reload (the finger is not held any more): it goes back, as on cancel.
 */
export function parseSavedTimer(raw: string | null): SavedTimer | null {
  if (!raw) {
    return null
  }
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return null
  }
  if (
    !isObject(data) || data.version !== SAVED_VERSION ||
    typeof data.owner !== 'string' || !isState(data.state)
  ) {
    return null
  }
  const { phase, holdStart, inspectionStart, solveStart, result, inspectionPenalty } = data.state
  const state = { phase, holdStart, inspectionStart, solveStart, result, inspectionPenalty }
  return { owner: data.owner, state: transition(state, { type: 'cancel', now: 0 }, { inspection: false }) }
}

export function serializeSavedTimer(saved: SavedTimer): string {
  return JSON.stringify({ version: SAVED_VERSION, owner: saved.owner, state: saved.state })
}

function isState(value: unknown): value is TimerState {
  if (!isObject(value)) {
    return false
  }
  const numbers = ['holdStart', 'solveStart', 'result'] as const
  return (
    PHASES.includes(value.phase as Phase) &&
    numbers.every((key) => Number.isFinite(value[key])) &&
    (value.inspectionStart === null || Number.isFinite(value.inspectionStart)) &&
    PENALTIES.includes(value.inspectionPenalty as string)
  )
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

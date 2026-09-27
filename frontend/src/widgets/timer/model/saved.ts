// Timer state in sessionStorage: survives a reload and a tab unloaded by the browser.
// Pure functions without Vue. Time in the state is ms since 1970 (timerNow),
// so the saved start moments are valid after a reload.
import { MAX_TIME } from '@/shared/lib'
import { timerNow } from './clock'
import { initialState, transition, type Phase, type TimerState } from './machine'

/** Storage format version. Data of another version is not read. */
export const SAVED_VERSION = 1

export interface SavedTimer {
  /** Whose solve: `training:<event_id>` or `series:<series_id>:<attempt>`. */
  owner: string
  state: TimerState
}

const PHASES: Phase[] = ['idle', 'inspection', 'holding', 'ready', 'running', 'stopped']
const PENALTIES = ['none', 'plus2', 'dnf']

/** An attempt is shorter than MAX_TIME: an older start is garbage, not a solve. */
const MAX_AGE_MS = MAX_TIME * 10
/** Allowance for rounding of performance.timeOrigin between page loads. */
const FUTURE_TOLERANCE_MS = 1000

/**
 * The saved timer. Never throws: broken data or another version gives null.
 * Holding does not survive a reload (the finger is not held any more): it goes back, as on cancel.
 * If the start of a running inspection or solve is in the future or older than an attempt
 * can last, the state is broken: the timer goes back to idle instead of showing garbage.
 */
export function parseSavedTimer(raw: string | null, now = timerNow()): SavedTimer | null {
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
  const restored = transition(state, { type: 'cancel', now: 0 }, { inspection: false })
  return { owner: data.owner, state: isFresh(restored, now) ? restored : initialState() }
}

export function serializeSavedTimer(saved: SavedTimer): string {
  return JSON.stringify({ version: SAVED_VERSION, owner: saved.owner, state: saved.state })
}

/** The start the shown time is counted from is not in the future and not too old. */
function isFresh(state: TimerState, now: number): boolean {
  const start =
    state.phase === 'running' ? state.solveStart
    : state.phase === 'inspection' ? state.inspectionStart
    : null
  return start === null || (start <= now + FUTURE_TOLERANCE_MS && now - start <= MAX_AGE_MS)
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

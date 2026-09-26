// Timer state machine: a pure transition function, time is passed in from outside
// (performance.now() at the event), so it is easy to test.
//
// idle ──press──▶ holding ──HOLD_MS──▶ ready ──release──▶ running ──press──▶ stopped
//   └─(with inspection) press ──▶ inspection ──press──▶ holding …
// Releasing in holding too early goes back (to idle or inspection).
// From stopped a new press starts the next solve, as from idle.

/** How long to hold the finger or space until ready. */
export const HOLD_MS = 300
/** Inspection: 15 seconds, up to 17 a +2 penalty, longer is DNF. */
export const INSPECTION_MS = 15_000
export const INSPECTION_DNF_MS = 17_000

export type Phase = 'idle' | 'inspection' | 'holding' | 'ready' | 'running' | 'stopped'
export type SuggestedPenalty = 'none' | 'plus2' | 'dnf'

export interface TimerState {
  phase: Phase
  /** Start of holding. */
  holdStart: number
  /** Start of inspection; null means a solve without inspection. */
  inspectionStart: number | null
  solveStart: number
  /** Solve time in hundredths of a second, known after stopping. */
  result: number
  /** Inspection penalty, offered to the participant after the solve. */
  inspectionPenalty: SuggestedPenalty
}

export interface TimerEvent {
  type: 'press' | 'release' | 'tick'
  now: number
}

export function initialState(): TimerState {
  return {
    phase: 'idle',
    holdStart: 0,
    inspectionStart: null,
    solveStart: 0,
    result: 0,
    inspectionPenalty: 'none',
  }
}

export function inspectionPenalty(elapsedMs: number): SuggestedPenalty {
  if (elapsedMs > INSPECTION_DNF_MS) return 'dnf'
  if (elapsedMs > INSPECTION_MS) return 'plus2'
  return 'none'
}

export function transition(
  state: TimerState,
  event: TimerEvent,
  options: { inspection: boolean },
): TimerState {
  const { phase } = state
  const { now } = event

  switch (event.type) {
    case 'press':
      if (phase === 'idle' || phase === 'stopped') {
        return options.inspection
          ? { ...initialState(), phase: 'inspection', inspectionStart: now }
          : { ...initialState(), phase: 'holding', holdStart: now }
      }
      if (phase === 'inspection') {
        return { ...state, phase: 'holding', holdStart: now }
      }
      if (phase === 'running') {
        // Hundredths: thousandths are dropped, as in result calculation.
        return { ...state, phase: 'stopped', result: Math.floor((now - state.solveStart) / 10) }
      }
      return state

    case 'release':
      if (phase === 'holding') {
        return { ...state, phase: state.inspectionStart === null ? 'idle' : 'inspection' }
      }
      if (phase === 'ready') {
        return {
          ...state,
          phase: 'running',
          solveStart: now,
          inspectionPenalty:
            state.inspectionStart === null ? 'none' : inspectionPenalty(now - state.inspectionStart),
        }
      }
      return state

    case 'tick':
      if (phase === 'holding' && now - state.holdStart >= HOLD_MS) {
        return { ...state, phase: 'ready' }
      }
      return state
  }
}

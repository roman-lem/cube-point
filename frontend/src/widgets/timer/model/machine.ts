// Машина состояний таймера: чистая функция переходов, время передаётся снаружи
// (performance.now() в момент события), поэтому её легко проверять тестами.
//
// idle ──нажатие──▶ holding ──HOLD_MS──▶ ready ──отпускание──▶ running ──нажатие──▶ stopped
//   └─(с инспекцией) нажатие ──▶ inspection ──нажатие──▶ holding …
// Отпускание в holding раньше срока возвращает назад (в idle или инспекцию).
// Из stopped новое нажатие начинает следующую сборку, как из idle.

/** Сколько держать палец или пробел до готовности. */
export const HOLD_MS = 300
/** Инспекция: 15 секунд, до 17 — штраф +2, дольше — DNF. */
export const INSPECTION_MS = 15_000
export const INSPECTION_DNF_MS = 17_000

export type Phase = 'idle' | 'inspection' | 'holding' | 'ready' | 'running' | 'stopped'
export type SuggestedPenalty = 'none' | 'plus2' | 'dnf'

export interface TimerState {
  phase: Phase
  /** Начало удержания. */
  holdStart: number
  /** Начало инспекции; null — сборка без инспекции. */
  inspectionStart: number | null
  solveStart: number
  /** Время сборки в сотых долях секунды, известно после остановки. */
  result: number
  /** Штраф за инспекцию, предлагается участнику после сборки. */
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
        // Сотые доли: тысячные отбрасываются, как в подсчёте результатов.
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

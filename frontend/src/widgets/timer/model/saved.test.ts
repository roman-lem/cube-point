// Timer state across a reload: the saved start moments give the right time.
import { describe, expect, it } from 'vitest'
import { HOLD_MS, initialState, transition, type TimerState } from './machine'
import { parseSavedTimer, serializeSavedTimer, SAVED_VERSION } from './saved'

// Moments are ms since 1970, as timerNow() gives them.
const T = 1_790_000_000_000

function running(): TimerState {
  return { ...initialState(), phase: 'running', holdStart: T - HOLD_MS, solveStart: T }
}

// The page is reloaded a second after the saved moments.
const NOW = T + 1000

function reload(owner: string, state: TimerState) {
  return parseSavedTimer(serializeSavedTimer({ owner, state }), NOW)
}

function raw(state: unknown, fields: Record<string, unknown> = {}) {
  return JSON.stringify({ version: SAVED_VERSION, owner: 'training:333', state, ...fields })
}

describe('saved timer', () => {
  it('a solve goes on after a reload with the time from the saved start', () => {
    const saved = reload('training:333', running())!
    expect(saved.owner).toBe('training:333')
    const stopped = transition(saved.state, { type: 'press', now: T + 12_345 }, { inspection: false })
    expect(stopped.phase).toBe('stopped')
    expect(stopped.result).toBe(1234)
  })

  it('inspection goes on from the saved start, the penalty is counted from it', () => {
    const inspection: TimerState = { ...initialState(), phase: 'inspection', inspectionStart: T }
    let state = reload('series:7:2', inspection)!.state
    expect(state).toEqual(inspection)
    const options = { inspection: true }
    state = transition(state, { type: 'press', now: T + 16_000 }, options)
    state = transition(state, { type: 'tick', now: T + 16_000 + HOLD_MS }, options)
    state = transition(state, { type: 'release', now: T + 16_500 }, options)
    expect(state.phase).toBe('running')
    expect(state.inspectionPenalty).toBe('plus2')
  })

  it('holding does not survive a reload', () => {
    const ready: TimerState = { ...initialState(), phase: 'ready', holdStart: T }
    expect(reload('training:333', ready)!.state.phase).toBe('idle')
    const inInspection: TimerState = { ...ready, inspectionStart: T - 5000 }
    expect(reload('training:333', inInspection)!.state.phase).toBe('inspection')
  })

  it('a stopped solve keeps its result', () => {
    const stopped: TimerState = { ...running(), phase: 'stopped', result: 987, inspectionPenalty: 'dnf' }
    expect(reload('series:7:2', stopped)!.state).toEqual(stopped)
  })

  it('does not carry extra fields', () => {
    expect(parseSavedTimer(raw({ ...running(), extra: 1 }), NOW)!.state).toEqual(running())
  })

  it.each([
    ['a solve started in the future', { ...running(), solveStart: NOW + 60_000 }],
    ['a solve older than an attempt can last', { ...running(), solveStart: NOW - 4 * 3600_000 }],
    ['an inspection started in the future', { ...initialState(), phase: 'inspection', inspectionStart: NOW + 60_000 }],
    ['an inspection from yesterday', { ...initialState(), phase: 'inspection', inspectionStart: NOW - 24 * 3600_000 }],
    // Moments of performance.now() from another page load, not ms since 1970.
    ['a start on another time scale', { ...running(), solveStart: 38_000 }],
  ] as [string, TimerState][])('a broken start (%s) resets the timer to idle', (_name, state) => {
    expect(reload('series:7:2', state)).toEqual({ owner: 'series:7:2', state: initialState() })
  })

  it('an old stopped solve keeps its result: its time does not run any more', () => {
    const stopped: TimerState = { ...running(), phase: 'stopped', solveStart: NOW - 24 * 3600_000, result: 987 }
    expect(reload('series:7:2', stopped)!.state).toEqual(stopped)
  })

  it.each([
    ['nothing', null],
    ['not JSON', '{'],
    ['an array', '[]'],
    ['another version', raw(running(), { version: SAVED_VERSION + 1 })],
    ['no owner', raw(running(), { owner: undefined })],
    ['unknown phase', raw({ ...running(), phase: 'go' })],
    ['bad start', raw({ ...running(), solveStart: 'now' })],
    ['bad inspection start', raw({ ...running(), inspectionStart: 'soon' })],
    ['bad penalty', raw({ ...running(), inspectionPenalty: 'dns' })],
  ])('broken data (%s) gives nothing', (_name, data) => {
    expect(parseSavedTimer(data, NOW)).toBeNull()
  })
})

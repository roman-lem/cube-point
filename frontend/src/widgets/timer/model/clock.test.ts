// Time on the timer screen with a fake clock: the time source is replaced, not the real clock used.
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { vi } from 'vitest'
import { timerNow } from './clock'
import {
  HOLD_MS,
  initialState,
  inspectionElapsed,
  solveElapsed,
  transition,
  type TimerEvent,
  type TimerState,
} from './machine'
import { parseSavedTimer, serializeSavedTimer } from './saved'
import { inspectionCountdown } from './useTimer'

/** A page load: timeOrigin in ms since 1970, performance.now() counts from zero. */
let page: { timeOrigin: number; now: number }

function loadPage(timeOrigin: number) {
  page = { timeOrigin, now: 0 }
  vi.stubGlobal('performance', { get timeOrigin() { return page.timeOrigin }, now: () => page.now })
}

function wait(ms: number) {
  page.now += ms
}

function send(state: TimerState, type: TimerEvent['type'], inspection: boolean) {
  return transition(state, { type, now: timerNow() }, { inspection })
}

/** What the screen shows: the inspection countdown or the solve time in hundredths. */
function countdown(state: TimerState) {
  return inspectionCountdown(inspectionElapsed(state, timerNow())!)
}

beforeEach(() => loadPage(1_790_483_300_000))
afterEach(() => vi.unstubAllGlobals())

describe('timer time', () => {
  it('is ms since 1970 on the page load scale', () => {
    wait(1234.5)
    expect(timerNow()).toBe(1_790_483_301_234.5)
  })

  it('inspection starts at 15 and counts down', () => {
    wait(20_000)
    const state = send(initialState(), 'press', true)
    expect(countdown(state)).toBe('15')
    wait(999)
    expect(countdown(state)).toBe('15')
    wait(2)
    expect(countdown(state)).toBe('14')
    wait(13_000)
    expect(countdown(state)).toBe('1')
    wait(1500)
    expect(countdown(state)).toBe('+2')
  })

  it('a solve starts at 0 and grows', () => {
    wait(20_000)
    let state = send(initialState(), 'press', false)
    wait(HOLD_MS)
    state = send(state, 'tick', false)
    state = send(state, 'release', false)
    expect(state.phase).toBe('running')
    expect(solveElapsed(state, timerNow())).toBe(0)
    wait(10)
    expect(solveElapsed(state, timerNow())).toBe(1)
    wait(38_000)
    expect(solveElapsed(state, timerNow())).toBe(3801)
  })

  it('after a reload the solve goes on with the right time', () => {
    wait(20_000)
    let state = send(initialState(), 'press', true)
    wait(5000)
    state = send(state, 'press', true)
    wait(HOLD_MS)
    state = send(state, 'tick', true)
    state = send(state, 'release', true)
    wait(12_000)
    const raw = serializeSavedTimer({ owner: 'training:333', state })

    // A new page: performance.now() starts from zero again, 3 s later on the wall clock.
    loadPage(page.timeOrigin + page.now + 3000)
    const saved = parseSavedTimer(raw)!
    expect(saved.state.phase).toBe('running')
    expect(solveElapsed(saved.state, timerNow())).toBe(1500)
    wait(1000)
    expect(solveElapsed(saved.state, timerNow())).toBe(1600)
  })

  it('after a reload the inspection goes on with the right countdown', () => {
    const state = send(initialState(), 'press', true)
    wait(4000)
    const raw = serializeSavedTimer({ owner: 'training:333', state })

    loadPage(page.timeOrigin + page.now + 2500)
    const saved = parseSavedTimer(raw)!
    expect(saved.state.phase).toBe('inspection')
    expect(countdown(saved.state)).toBe('9')
  })

  it('a broken saved start resets the timer to idle', () => {
    // A start of performance.now() of another page load: a small number, not ms since 1970.
    const broken: TimerState = { ...initialState(), phase: 'running', holdStart: 37_700, solveStart: 38_000 }
    const saved = parseSavedTimer(serializeSavedTimer({ owner: 'training:333', state: broken }))!
    expect(saved.state).toEqual(initialState())
    expect(solveElapsed(saved.state, timerNow())).toBe(0)
  })
})

describe('timer code', () => {
  // The timer has one time source: mixing it with performance.now() or Date.now() shows garbage.
  const sources = import.meta.glob(['../**/*.ts', '../**/*.vue', '!../**/*.test.ts', '!./clock.ts'], {
    query: '?raw',
    import: 'default',
    eager: true,
  }) as Record<string, string>

  it.each(Object.entries(sources))('%s takes time only from timerNow()', (_path, code) => {
    expect(code).not.toMatch(/performance\.now\(|Date\.now\(/)
  })
})

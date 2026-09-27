import { describe, expect, it } from 'vitest'
import {
  HOLD_MS,
  initialState,
  isFocused,
  transition,
  type TimerEvent,
  type TimerState,
} from './machine'

function run(events: [TimerEvent['type'], number][], inspection = false): TimerState {
  return events.reduce(
    (state, [type, now]) => transition(state, { type, now }, { inspection }),
    initialState(),
  )
}

describe('timer without inspection', () => {
  it('hold, start and stop', () => {
    const state = run([
      ['press', 0],
      ['tick', HOLD_MS],
      ['release', 400],
      ['press', 400 + 9876.9],
    ])
    expect(state.phase).toBe('stopped')
    expect(state.result).toBe(987)
    expect(state.inspectionPenalty).toBe('none')
  })

  it('a short press does not start the timer', () => {
    expect(run([['press', 0], ['tick', 100], ['release', 150]]).phase).toBe('idle')
  })

  it('while held, the timer is ready but not running', () => {
    expect(run([['press', 0], ['tick', HOLD_MS]]).phase).toBe('ready')
  })

  it('after stopping, a press starts a new solve', () => {
    const state = run([
      ['press', 0], ['tick', HOLD_MS], ['release', 400], ['press', 1400], ['release', 1500],
      ['press', 2000],
    ])
    expect(state.phase).toBe('holding')
  })

  it('releasing after stopping changes nothing', () => {
    const state = run([
      ['press', 0], ['tick', HOLD_MS], ['release', 400], ['press', 1400], ['release', 1500],
    ])
    expect(state.phase).toBe('stopped')
    expect(state.result).toBe(100)
  })
})

describe('inspection', () => {
  const solveAfter = (inspectionMs: number) =>
    run(
      [
        ['press', 0],
        ['release', 100],
        ['press', inspectionMs - HOLD_MS],
        ['tick', inspectionMs],
        ['release', inspectionMs],
        ['press', inspectionMs + 1000],
      ],
      true,
    )

  it('the first press starts inspection, releasing does not interrupt it', () => {
    expect(run([['press', 0], ['release', 100]], true).phase).toBe('inspection')
  })

  it('a short press during inspection returns to inspection', () => {
    const state = run([['press', 0], ['release', 100], ['press', 5000], ['release', 5100]], true)
    expect(state.phase).toBe('inspection')
    expect(state.inspectionStart).toBe(0)
  })

  it.each([
    [10_000, 'none'],
    [15_000, 'none'],
    [15_001, 'plus2'],
    [17_000, 'plus2'],
    [17_001, 'dnf'],
  ] as const)('start after %i ms gives penalty %s', (inspectionMs, penalty) => {
    const state = solveAfter(inspectionMs)
    expect(state.phase).toBe('stopped')
    expect(state.result).toBe(100)
    expect(state.inspectionPenalty).toBe(penalty)
  })
})

describe('the tab goes to the background (cancel)', () => {
  it('holding without inspection goes back to idle', () => {
    expect(run([['press', 0], ['cancel', 100]]).phase).toBe('idle')
  })

  it('ready does not start the solve, a later release changes nothing', () => {
    const state = run([['press', 0], ['tick', HOLD_MS], ['cancel', 400], ['release', 500]])
    expect(state.phase).toBe('idle')
  })

  it('with inspection, ready goes back to inspection with the same start', () => {
    const state = run(
      [['press', 0], ['release', 100], ['press', 5000], ['tick', 5000 + HOLD_MS], ['cancel', 5400]],
      true,
    )
    expect(state.phase).toBe('inspection')
    expect(state.inspectionStart).toBe(0)
  })

  it('inspection goes on', () => {
    const state = run([['press', 0], ['release', 100], ['cancel', 3000]], true)
    expect(state.phase).toBe('inspection')
    expect(state.inspectionStart).toBe(0)
  })

  it('the solve goes on, the time is counted from the start', () => {
    const state = run([
      ['press', 0], ['tick', HOLD_MS], ['release', 400], ['cancel', 5000], ['press', 10_400],
    ])
    expect(state.phase).toBe('stopped')
    expect(state.result).toBe(1000)
  })
})

describe('leaving the screen (abort)', () => {
  it('stops the solve with the time at that moment', () => {
    const state = run([['press', 0], ['tick', HOLD_MS], ['release', 400], ['abort', 2400]])
    expect(state.phase).toBe('stopped')
    expect(state.result).toBe(200)
  })

  it('keeps the inspection penalty of the stopped solve', () => {
    const state = run(
      [
        ['press', 0], ['release', 100], ['press', 15_500], ['tick', 15_500 + HOLD_MS],
        ['release', 16_000], ['abort', 20_000],
      ],
      true,
    )
    expect(state.phase).toBe('stopped')
    expect(state.result).toBe(400)
    expect(state.inspectionPenalty).toBe('plus2')
  })

  const beforeStart: [string, [TimerEvent['type'], number][]][] = [
    ['inspection', [['press', 0], ['release', 100]]],
    ['holding', [['press', 0], ['release', 100], ['press', 3000]]],
    ['ready', [['press', 0], ['release', 100], ['press', 3000], ['tick', 3000 + HOLD_MS]]],
  ]

  it.each(beforeStart)('from %s goes to idle', (phase, events) => {
    const before = run(events, true)
    expect(before.phase).toBe(phase)
    expect(transition(before, { type: 'abort', now: 5000 }, { inspection: true })).toEqual(
      initialState(),
    )
  })

  it('changes nothing after stopping', () => {
    const stopped = run([['press', 0], ['tick', HOLD_MS], ['release', 400], ['press', 1400]])
    expect(transition(stopped, { type: 'abort', now: 9000 }, { inspection: false })).toBe(stopped)
  })
})

describe('only the timer on the screen (isFocused)', () => {
  const cases: [string, [TimerEvent['type'], number][], boolean, boolean][] = [
    ['idle', [], false, false],
    ['holding without inspection', [['press', 0]], false, false],
    ['ready without inspection', [['press', 0], ['tick', HOLD_MS]], false, false],
    ['running', [['press', 0], ['tick', HOLD_MS], ['release', 400]], false, true],
    ['stopped', [['press', 0], ['tick', HOLD_MS], ['release', 400], ['press', 900]], false, false],
    ['inspection', [['press', 0], ['release', 100]], true, true],
    ['holding in inspection', [['press', 0], ['release', 100], ['press', 3000]], true, true],
  ]

  it.each(cases)('%s', (_name, events, inspection, focused) => {
    expect(isFocused(run(events, inspection))).toBe(focused)
  })
})

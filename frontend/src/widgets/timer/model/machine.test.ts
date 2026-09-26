import { describe, expect, it } from 'vitest'
import {
  HOLD_MS,
  initialState,
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

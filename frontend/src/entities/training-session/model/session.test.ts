import { describe, expect, it } from 'vitest'
import { DNF } from '@/shared/lib'
import {
  SESSION_VERSION,
  addSolve,
  parseSession,
  removeSolve,
  serializeSession,
  sessionStats,
  setPenalty,
  type TrainingSolve,
} from './session'

const solve = (value: number, at: number, penalty: TrainingSolve['penalty'] = 'none') => ({
  value,
  penalty,
  at,
})

const stored = (solves: unknown, version: unknown = SESSION_VERSION) =>
  JSON.stringify({ version, solves })

describe('parseSession', () => {
  it('reads a saved session', () => {
    const solves = [solve(1000, 1), solve(1100, 2, 'plus2'), solve(900, 3, 'dnf')]

    expect(parseSession(serializeSession(solves))).toEqual(solves)
  })

  it.each([
    ['no data', null],
    ['empty string', ''],
    ['broken JSON', '{"version": 1, "solves": ['],
    ['not an object', '42'],
    ['array instead of object', JSON.stringify([solve(1000, 1)])],
    ['null in JSON', 'null'],
    ['another version', stored([solve(1000, 1)], 2)],
    ['no version', JSON.stringify({ solves: [solve(1000, 1)] })],
    ['version as a string', stored([solve(1000, 1)], '1')],
    ['solves is not an array', stored({ 0: solve(1000, 1) })],
    ['no solves', JSON.stringify({ version: SESSION_VERSION })],
  ])('%s: empty session', (_, raw) => {
    expect(parseSession(raw)).toEqual([])
  })

  it('drops only invalid solves', () => {
    const raw = stored([
      solve(1000, 1),
      null,
      'solve',
      { value: 1100, penalty: 'none' }, // no at
      { value: 11.5, penalty: 'none', at: 2 }, // fractional time
      { value: -100, penalty: 'none', at: 3 },
      { value: 0, penalty: 'none', at: 4 },
      { value: '1000', penalty: 'none', at: 5 },
      { value: 1000, penalty: 'dns', at: 6 }, // training has no DNS
      { value: 1000, penalty: 'oops', at: 7 },
      { value: null, penalty: 'dnf', at: 8 }, // a training solve always has a time
      { value: 1000, penalty: 'none', at: '9' },
      solve(1200, 10, 'plus2'),
      solve(1300, 10), // repeated at
      solve(900, 11, 'dnf'),
    ])

    expect(parseSession(raw)).toEqual([
      solve(1000, 1),
      solve(1200, 10, 'plus2'),
      solve(900, 11, 'dnf'),
    ])
  })

  it('extra solve fields are not kept', () => {
    const raw = stored([{ ...solve(1000, 1), scramble: "R U R'" }])

    expect(parseSession(raw)).toEqual([solve(1000, 1)])
  })
})

describe('session changes', () => {
  it('addSolve appends a solve with its moment', () => {
    const solves = addSolve([solve(1000, 100)], 1100, 'plus2', 500)

    expect(solves).toEqual([solve(1000, 100), solve(1100, 500, 'plus2')])
  })

  it('addSolve does not repeat at even if the clock is behind', () => {
    const solves = addSolve([solve(1000, 500)], 1100, 'none', 500)

    expect(solves.map((s) => s.at)).toEqual([500, 501])
  })

  it('setPenalty and removeSolve change only the target solve and leave the source array intact', () => {
    const solves = [solve(1000, 1), solve(1100, 2)]

    expect(setPenalty(solves, 2, 'dnf')).toEqual([solve(1000, 1), solve(1100, 2, 'dnf')])
    expect(removeSolve(solves, 1)).toEqual([solve(1100, 2)])
    expect(solves).toEqual([solve(1000, 1), solve(1100, 2)])
  })
})

describe('sessionStats', () => {
  it('empty session', () => {
    expect(sessionStats([])).toEqual({ ao5: null, ao12: null, best: null, count: 0 })
  })

  it('ao5 over the last five solves, no ao12 yet', () => {
    const values = [500, 1000, 1100, 1200, 1300, 1400]
    const solves = values.map((v, i) => solve(v, i + 1))

    expect(sessionStats(solves)).toEqual({ ao5: 1200, ao12: null, best: 500, count: 6 })
  })

  it('+2 counts, DNF is never the best', () => {
    const solves = [solve(800, 1, 'dnf'), solve(1000, 2, 'plus2'), solve(1100, 3)]

    expect(sessionStats(solves).best).toBe(1100)
  })

  it('all DNF: best is DNF', () => {
    expect(sessionStats([solve(1000, 1, 'dnf')]).best).toBe(DNF)
  })

  it('ao12 of twelve solves', () => {
    const solves = Array.from({ length: 12 }, (_, i) => solve(1000 + i * 100, i + 1))

    // 10.00 and 21.00 are dropped, average of 11.00 … 20.00.
    expect(sessionStats(solves).ao12).toBe(1550)
  })
})

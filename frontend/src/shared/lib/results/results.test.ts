// Result calculation checked against the cases shared with the backend.
import { describe, expect, it } from 'vitest'
import cases from '../../../../../testdata/results_cases.json'
import {
  averageOf,
  calcSeries,
  formatAttempt,
  formatResult,
  rollingAverages,
  type Attempt,
  type ResultType,
  type SeriesFormat,
  type SeriesResult,
} from './results'

interface SeriesCase {
  name: string
  format: SeriesFormat
  resultType: ResultType
  attempts: (Attempt | null)[]
  expected: SeriesResult
}

interface WindowCase<T> {
  name: string
  n: number
  resultType: ResultType
  attempts: Attempt[]
  expected: T
}

interface FormatResultCase {
  value: number | null
  resultType: ResultType
  isAverage: boolean
  expected: string
}

interface FormatAttemptCase {
  attempt: Attempt | null
  resultType: ResultType
  expected: string
}

describe('calcSeries', () => {
  it.each(cases.calcSeries as SeriesCase[])('$name', (c) => {
    expect(calcSeries(c.attempts, c.format, c.resultType)).toEqual(c.expected)
  })
})

describe('calcSeries: errors', () => {
  it.each(cases.calcSeriesErrors as Omit<SeriesCase, 'expected'>[])('$name', (c) => {
    expect(() => calcSeries(c.attempts, c.format, c.resultType)).toThrow()
  })
})

describe('formatResult', () => {
  it.each(cases.formatResult as FormatResultCase[])(
    '$value ($resultType, average: $isAverage) → $expected',
    (c) => {
      expect(formatResult(c.value, c.resultType, c.isAverage)).toBe(c.expected)
    },
  )
})

describe('formatAttempt', () => {
  it.each(cases.formatAttempt as FormatAttemptCase[])('$attempt ($resultType) → $expected', (c) => {
    expect(formatAttempt(c.attempt, c.resultType)).toBe(c.expected)
  })
})

describe('averageOf', () => {
  it.each(cases.averageOf as WindowCase<number | null>[])('$name', (c) => {
    expect(averageOf(c.attempts, c.n, c.resultType)).toBe(c.expected)
  })
})

describe('averageOf: errors', () => {
  it.each(cases.averageOfErrors as Omit<WindowCase<never>, 'expected'>[])('$name', (c) => {
    expect(() => averageOf(c.attempts, c.n, c.resultType)).toThrow()
  })
})

describe('rollingAverages', () => {
  it.each(cases.rollingAverages as WindowCase<(number | null)[]>[])('$name', (c) => {
    expect(rollingAverages(c.attempts, c.n, c.resultType)).toEqual(c.expected)
  })
})

describe('rollingAverages: errors', () => {
  it.each(cases.rollingAveragesErrors as Omit<WindowCase<never>, 'expected'>[])('$name', (c) => {
    expect(() => rollingAverages(c.attempts, c.n, c.resultType)).toThrow()
  })
})

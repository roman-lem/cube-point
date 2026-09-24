// Проверка подсчёта результатов по общим случаям с бэкендом.
import { describe, expect, it } from 'vitest'
import cases from '../../../../../testdata/results_cases.json'
import {
  calcSeries,
  formatAttempt,
  formatResult,
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

describe('calcSeries: ошибки', () => {
  it.each(cases.calcSeriesErrors as Omit<SeriesCase, 'expected'>[])('$name', (c) => {
    expect(() => calcSeries(c.attempts, c.format, c.resultType)).toThrow()
  })
})

describe('formatResult', () => {
  it.each(cases.formatResult as FormatResultCase[])(
    '$value ($resultType, среднее: $isAverage) → $expected',
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

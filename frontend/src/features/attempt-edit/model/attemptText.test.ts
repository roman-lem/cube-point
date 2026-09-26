import { describe, expect, it } from 'vitest'
import type { Attempt } from '@/shared/lib'
import { attemptToText, parseAttemptText, toggleDnf, togglePlus2 } from './attemptText'

describe('parseAttemptText', () => {
  it.each<[string, Attempt]>([
    ['1234', { value: 1234, penalty: 'none' }],
    ['10234', { value: 6234, penalty: 'none' }],
    ['12.34', { value: 1234, penalty: 'none' }],
    ['1:02.34', { value: 6234, penalty: 'none' }],
    ['1234+', { value: 1234, penalty: 'plus2' }],
    ['12.34 +2', { value: 1234, penalty: 'plus2' }],
    ['d', { value: null, penalty: 'dnf' }],
    ['DNF', { value: null, penalty: 'dnf' }],
    ['1234d', { value: 1234, penalty: 'dnf' }],
    ['12.34 DNF', { value: 1234, penalty: 'dnf' }],
    ['dns', { value: null, penalty: 'dns' }],
    ['234567', { value: 142567, penalty: 'none' }],
    ['1052345', { value: 392345, penalty: 'none' }],
    ['1:05:23.45+', { value: 392345, penalty: 'plus2' }],
    ['1052345 d', { value: 392345, penalty: 'dnf' }],
  ])('time: %s', (text, expected) => {
    expect(parseAttemptText(text, 'time')).toEqual(expected)
  })

  it.each(['', '+', 'abc', '12..3', '1:75', '0', '12 x', '3000000', '1:60:00'])('invalid time input: "%s"', (text) => {
    expect(parseAttemptText(text, 'time')).toBeNull()
  })

  it('FMC moves', () => {
    expect(parseAttemptText('28', 'moves')).toEqual({ value: 28, penalty: 'none' })
    expect(parseAttemptText('d', 'moves')).toEqual({ value: null, penalty: 'dnf' })
    expect(parseAttemptText('28+', 'moves')).toBeNull()
    expect(parseAttemptText('81', 'moves')).toBeNull()
    expect(parseAttemptText('2.5', 'moves')).toBeNull()
  })
})

describe('attemptToText', () => {
  it.each<[Attempt, string]>([
    [{ value: 1234, penalty: 'none' }, '12.34'],
    [{ value: 6234, penalty: 'plus2' }, '1:02.34+'],
    [{ value: 392345, penalty: 'none' }, '1:05:23.45'],
    [{ value: 1234, penalty: 'dnf' }, '12.34 DNF'],
    [{ value: null, penalty: 'dnf' }, 'DNF'],
    [{ value: null, penalty: 'dns' }, 'DNS'],
  ])('%o → "%s" and back', (attempt, text) => {
    expect(attemptToText(attempt, 'time')).toBe(text)
    expect(parseAttemptText(text, 'time')).toEqual(attempt)
  })

  it('empty attempt gives empty text', () => {
    expect(attemptToText(null, 'time')).toBe('')
  })
})

describe('penalties by keys', () => {
  it('+ toggles +2', () => {
    expect(togglePlus2({ value: 1000, penalty: 'none' })).toEqual({ value: 1000, penalty: 'plus2' })
    expect(togglePlus2({ value: 1000, penalty: 'plus2' })).toEqual({ value: 1000, penalty: 'none' })
    expect(togglePlus2({ value: null, penalty: 'dnf' })).toBeNull()
    expect(togglePlus2(null)).toBeNull()
  })

  it('d sets and removes DNF, keeping the time', () => {
    expect(toggleDnf({ value: 1000, penalty: 'plus2' })).toEqual({ value: 1000, penalty: 'dnf' })
    expect(toggleDnf({ value: 1000, penalty: 'dnf' })).toEqual({ value: 1000, penalty: 'none' })
    expect(toggleDnf(null)).toEqual({ value: null, penalty: 'dnf' })
    expect(toggleDnf({ value: null, penalty: 'dnf' })).toBeNull()
  })
})

import { describe, expect, it } from 'vitest'
import { tokenFromHash } from './linkToken'

describe('tokenFromHash', () => {
  it('reads the token from the fragment', () => {
    expect(tokenFromHash('#token=abc-DEF_123')).toBe('abc-DEF_123')
  })

  it('works without the leading #', () => {
    expect(tokenFromHash('token=abc')).toBe('abc')
  })

  it('is empty without a token', () => {
    expect(tokenFromHash('')).toBe('')
    expect(tokenFromHash('#processing')).toBe('')
  })
})

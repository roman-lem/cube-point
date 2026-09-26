import { describe, expect, it } from 'vitest'
import { movesWord } from './moves'

describe('movesWord', () => {
  it.each([
    [1, 'ход'], [21, 'ход'], [3, 'хода'], [24, 'хода'], [11, 'ходов'], [25, 'ходов'],
  ])('%i → %s', (value, word) => {
    expect(movesWord(value)).toBe(word)
  })

  it('a mean uses «хода»', () => {
    expect(movesWord(2533, true)).toBe('хода')
  })
})

import { describe, expect, it } from 'vitest'
import { parseTimeInput } from './timeInput'

describe('parseTimeInput', () => {
  it.each([
    ['9.87', 987],
    ['9,87', 987],
    ['12.3', 1230],
    ['12', 12],
    [' 11.02 ', 1102],
    ['75.5', 7550],
    ['1:02.45', 6245],
    ['1:02', 6200],
    ['987', 987],
    ['5', 5],
    ['10245', 6245],
    ['1000000', 600000],
  ])('%s → %i', (text, expected) => {
    expect(parseTimeInput(text)).toBe(expected)
  })

  it.each(['', 'abc', '0', '0.00', '1:75.00', '1:5.00', '9.876', '-5', '1.2.3', '17500'])(
    'rejects "%s"',
    (text) => {
      expect(parseTimeInput(text)).toBeNull()
    },
  )
})

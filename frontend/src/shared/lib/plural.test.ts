import { describe, expect, it } from 'vitest'
import { plural } from './plural'

const FORMS: [string, string, string] = ['участник', 'участника', 'участников']

describe('plural', () => {
  it.each([
    [0, '0 участников'],
    [1, '1 участник'],
    [2, '2 участника'],
    [5, '5 участников'],
    [11, '11 участников'],
    [12, '12 участников'],
    [21, '21 участник'],
    [22, '22 участника'],
    [111, '111 участников'],
  ])('%i', (count, expected) => {
    expect(plural(count, FORMS)).toBe(expected)
  })
})

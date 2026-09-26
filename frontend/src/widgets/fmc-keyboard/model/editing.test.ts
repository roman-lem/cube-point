import { describe, expect, it } from 'vitest'
import { addMove, removeLast, setModifier } from './editing'

describe('FMC keyboard', () => {
  it('adds faces and rotations', () => {
    expect(addMove(addMove([], 'R', false), 'x', false)).toEqual(['R', 'x'])
  })

  it('w makes a wide turn for faces only', () => {
    expect(addMove([], 'U', true)).toEqual(['Uw'])
    expect(addMove([], 'y', true)).toEqual(['y'])
  })

  it("' and 2 change the last move", () => {
    expect(setModifier(['R', 'U'], "'")).toEqual(['R', "U'"])
    expect(setModifier(["Rw'"], '2')).toEqual(['Rw2'])
    expect(setModifier(['x2'], "'")).toEqual(["x'"])
  })

  it('a repeated modifier is removed', () => {
    expect(setModifier(["R'"], "'")).toEqual(['R'])
    expect(setModifier(['Fw2'], '2')).toEqual(['Fw'])
  })

  it('a modifier without moves does nothing', () => {
    expect(setModifier([], '2')).toEqual([])
  })

  it('backspace removes one move', () => {
    expect(removeLast(['R', "U'", 'Fw2'])).toEqual(['R', "U'"])
    expect(removeLast([])).toEqual([])
  })
})

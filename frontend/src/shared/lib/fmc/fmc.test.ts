import { describe, expect, it } from 'vitest'
import { checkSolution, countMoves, parseSolution } from './fmc'

const pairs = (n: number) => Array(n).fill("R R'").join(' ')

describe('countMoves', () => {
  it('faces and wide turns count one move each, doubles included', () => {
    expect(countMoves(parseSolution("R U2 F' Rw Lw2 Dw'"))).toBe(6)
  })

  it('rotations do not count', () => {
    expect(countMoves(parseSolution("x R y2 U z' F"))).toBe(3)
  })
})

describe('checkSolution', () => {
  it('a correct solution gives the move count', async () => {
    expect(await checkSolution('R U F', "F' U' R'")).toEqual({ moves: 3 })
  })

  it('a wrong solution is DNF', async () => {
    expect(await checkSolution('R U F', "F' U'")).toEqual({ dnf: 'not_solved' })
  })

  it('cube solved in another orientation', async () => {
    expect(await checkSolution('R U F', "F' U' R' x y")).toEqual({ moves: 3 })
  })

  it('a rotation in the middle of the solution changes the faces', async () => {
    // After y the right face is in front.
    expect(await checkSolution('R', "y F'")).toEqual({ moves: 1 })
    expect(await checkSolution('R', "y R'")).toEqual({ dnf: 'not_solved' })
  })

  it('wide turns', async () => {
    expect(await checkSolution('Rw', "x' L'")).toEqual({ moves: 1 })
    expect(await checkSolution('Rw2 U', "U' Rw2")).toEqual({ moves: 2 })
  })

  it('double moves', async () => {
    expect(await checkSolution('R2 U2', 'U2 R2')).toEqual({ moves: 2 })
  })

  it('slices are DNF even if the cube is solved', async () => {
    expect(await checkSolution('M', "M'")).toEqual({ dnf: 'slice' })
    expect(await checkSolution('R', "R' E E'")).toEqual({ dnf: 'slice' })
    expect(await checkSolution('R', "R' S2 S2")).toEqual({ dnf: 'slice' })
  })

  it('empty solution and unknown moves are DNF', async () => {
    expect(await checkSolution('R', '')).toEqual({ dnf: 'empty' })
    expect(await checkSolution('R', '   ')).toEqual({ dnf: 'empty' })
    expect(await checkSolution('R', "R3")).toEqual({ dnf: 'invalid' })
    expect(await checkSolution('R', "r'")).toEqual({ dnf: 'invalid' })
  })

  it('at most 80 moves', async () => {
    expect(await checkSolution('R U', `U' R' ${pairs(39)}`)).toEqual({ moves: 80 })
    expect(await checkSolution('R U', `U' R' ${pairs(40)}`)).toEqual({ dnf: 'too_long' })
  })

  it('rotations do not count towards the limit', async () => {
    expect(await checkSolution('R U', `U' R' ${pairs(39)} x y z`)).toEqual({ moves: 80 })
  })
})

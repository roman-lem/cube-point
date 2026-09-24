import { describe, expect, it } from 'vitest'
import { checkSolution, countMoves, parseSolution } from './fmc'

const pairs = (n: number) => Array(n).fill("R R'").join(' ')

describe('countMoves', () => {
  it('грани и широкие повороты по одному ходу, включая двойные', () => {
    expect(countMoves(parseSolution("R U2 F' Rw Lw2 Dw'"))).toBe(6)
  })

  it('перехваты не считаются', () => {
    expect(countMoves(parseSolution("x R y2 U z' F"))).toBe(3)
  })
})

describe('checkSolution', () => {
  it('верное решение — число ходов', async () => {
    expect(await checkSolution('R U F', "F' U' R'")).toEqual({ moves: 3 })
  })

  it('неверное решение — DNF', async () => {
    expect(await checkSolution('R U F', "F' U'")).toEqual({ dnf: 'not_solved' })
  })

  it('куб собран в другой ориентации', async () => {
    expect(await checkSolution('R U F', "F' U' R' x y")).toEqual({ moves: 3 })
  })

  it('перехват в середине решения меняет грани', async () => {
    // После y правая грань оказывается спереди.
    expect(await checkSolution('R', "y F'")).toEqual({ moves: 1 })
    expect(await checkSolution('R', "y R'")).toEqual({ dnf: 'not_solved' })
  })

  it('широкие повороты', async () => {
    expect(await checkSolution('Rw', "x' L'")).toEqual({ moves: 1 })
    expect(await checkSolution('Rw2 U', "U' Rw2")).toEqual({ moves: 2 })
  })

  it('двойные ходы', async () => {
    expect(await checkSolution('R2 U2', 'U2 R2')).toEqual({ moves: 2 })
  })

  it('срезы — DNF, даже если куб собран', async () => {
    expect(await checkSolution('M', "M'")).toEqual({ dnf: 'slice' })
    expect(await checkSolution('R', "R' E E'")).toEqual({ dnf: 'slice' })
    expect(await checkSolution('R', "R' S2 S2")).toEqual({ dnf: 'slice' })
  })

  it('пустое решение и неизвестные ходы — DNF', async () => {
    expect(await checkSolution('R', '')).toEqual({ dnf: 'empty' })
    expect(await checkSolution('R', '   ')).toEqual({ dnf: 'empty' })
    expect(await checkSolution('R', "R3")).toEqual({ dnf: 'invalid' })
    expect(await checkSolution('R', "r'")).toEqual({ dnf: 'invalid' })
  })

  it('не больше 80 ходов', async () => {
    expect(await checkSolution('R U', `U' R' ${pairs(39)}`)).toEqual({ moves: 80 })
    expect(await checkSolution('R U', `U' R' ${pairs(40)}`)).toEqual({ dnf: 'too_long' })
  })

  it('перехваты не входят в лимит', async () => {
    expect(await checkSolution('R U', `U' R' ${pairs(39)} x y z`)).toEqual({ moves: 80 })
  })
})

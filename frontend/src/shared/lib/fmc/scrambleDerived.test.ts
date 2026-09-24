import { describe, expect, it } from 'vitest'
import { checkSolution, parseSolution } from './fmc'
import { isScrambleDerived, toFaceTurns } from './scrambleDerived'

const SCRAMBLE = "R' U' F D2 B2 L2 U2 F' L2 R2 U2 B' D2 F' R' B U' L F' D' B2 R' U' F"
// Обратный скрамбл целиком.
const INVERSE = "F' U R B2 D F L' U B' R F D2 B U2 R2 L2 F U2 L2 B2 D2 F' U R"

const derived = (solution: string) =>
  isScrambleDerived(parseSolution(SCRAMBLE), parseSolution(solution))

describe('toFaceTurns', () => {
  it('без перехватов ходы не меняются', () => {
    expect(toFaceTurns(parseSolution("R U2 F'"))).toEqual(['R', 'U2', "F'"])
  })

  it('перехваты переименовывают грани', () => {
    // После y спереди оказывается бывшая правая грань.
    expect(toFaceTurns(parseSolution("y F'"))).toEqual(["R'"])
    expect(toFaceTurns(parseSolution('x U'))).toEqual(['F'])
    expect(toFaceTurns(parseSolution("z' U"))).toEqual(['R'])
    expect(toFaceTurns(parseSolution('y2 R'))).toEqual(['L'])
  })

  it('широкий поворот — противоположная грань и перехват', () => {
    expect(toFaceTurns(parseSolution('Rw U'))).toEqual(['L', 'F'])
    expect(toFaceTurns(parseSolution("Lw' U"))).toEqual(["R'", 'F'])
    expect(toFaceTurns(parseSolution('Uw2 F'))).toEqual(['D2', 'B'])
  })

  // Сверка с cubing.js: повороты граней должны давать то же состояние куба,
  // что и исходное решение (с точностью до ориентации).
  it.each([
    "y F' x2 R Uw L' z D2",
    "Rw U' Fw2 x' B Lw' y2 Dw R",
    "z Bw' U x y' Lw2 F' Uw' D",
  ])('те же ходы, что и %s', async (solution) => {
    const { cube3x3x3 } = await import('cubing/puzzles')
    const kpuzzle = await cube3x3x3.kpuzzle()
    const inverseTurns = toFaceTurns(parseSolution(solution))
      .reverse()
      .map((m) => (m.endsWith('2') ? m : m.endsWith("'") ? m.slice(0, -1) : `${m}'`))
      .join(' ')
    const solved = kpuzzle
      .defaultPattern()
      .applyAlg(inverseTurns)
      .applyAlg(solution)
      .experimentalIsSolved({ ignorePuzzleOrientation: true, ignoreCenterOrientation: true })
    expect(solved).toBe(true)
  })
})

describe('isScrambleDerived', () => {
  it('обратный скрамбл целиком', () => {
    expect(derived(INVERSE)).toBe(true)
  })

  it('часть обратного скрамбла от 6 ходов подряд', () => {
    expect(derived("R U B' R F D2 B U2 R2 L2 D")).toBe(true)
  })

  it('5 ходов подряд — ещё не нарушение', () => {
    // B' R F D2 B — 5 ходов обратного скрамбла, соседние ходы не совпадают.
    expect(derived("R D B' R F D2 B D")).toBe(false)
  })

  it('перехваты и широкие повороты не скрывают обратный скрамбл', () => {
    // "B' R F D2 B U2" после y: B→R, R→F, F→L, L→B.
    expect(derived("y R' F L D2 R U2")).toBe(true)
    // "F L' U B' R F": Rw' = L' x', после x' сверху бывшая B, спереди бывшая U.
    expect(derived("F Rw' F U' R D")).toBe(true)
  })

  it('обычное решение не считается полученным из скрамбла', () => {
    expect(derived("D' R2 U F2 L' B U' R D2 F' L2 U2 B")).toBe(false)
  })
})

describe('checkSolution и скрамбл', () => {
  it('решение из обратного скрамбла — DNF, хоть куб и собран', async () => {
    expect(await checkSolution(SCRAMBLE, INVERSE)).toEqual({ dnf: 'scramble_derived' })
  })
})

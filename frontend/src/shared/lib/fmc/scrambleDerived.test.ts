import { describe, expect, it } from 'vitest'
import { checkSolution, parseSolution } from './fmc'
import { isScrambleDerived, toFaceTurns } from './scrambleDerived'

const SCRAMBLE = "R' U' F D2 B2 L2 U2 F' L2 R2 U2 B' D2 F' R' B U' L F' D' B2 R' U' F"
// The whole inverse scramble.
const INVERSE = "F' U R B2 D F L' U B' R F D2 B U2 R2 L2 F U2 L2 B2 D2 F' U R"

const derived = (solution: string) =>
  isScrambleDerived(parseSolution(SCRAMBLE), parseSolution(solution))

describe('toFaceTurns', () => {
  it('without rotations the moves do not change', () => {
    expect(toFaceTurns(parseSolution("R U2 F'"))).toEqual(['R', 'U2', "F'"])
  })

  it('rotations rename the faces', () => {
    // After y the former right face is in front.
    expect(toFaceTurns(parseSolution("y F'"))).toEqual(["R'"])
    expect(toFaceTurns(parseSolution('x U'))).toEqual(['F'])
    expect(toFaceTurns(parseSolution("z' U"))).toEqual(['R'])
    expect(toFaceTurns(parseSolution('y2 R'))).toEqual(['L'])
  })

  it('a wide turn is the opposite face plus a rotation', () => {
    expect(toFaceTurns(parseSolution('Rw U'))).toEqual(['L', 'F'])
    expect(toFaceTurns(parseSolution("Lw' U"))).toEqual(["R'", 'F'])
    expect(toFaceTurns(parseSolution('Uw2 F'))).toEqual(['D2', 'B'])
  })

  // Cross-check with cubing.js: the face turns must give the same cube state
  // as the original solution (up to orientation).
  it.each([
    "y F' x2 R Uw L' z D2",
    "Rw U' Fw2 x' B Lw' y2 Dw R",
    "z Bw' U x y' Lw2 F' Uw' D",
  ])('same moves as %s', async (solution) => {
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
  it('the whole inverse scramble', () => {
    expect(derived(INVERSE)).toBe(true)
  })

  it('part of the inverse scramble of 6+ consecutive moves', () => {
    expect(derived("R U B' R F D2 B U2 R2 L2 D")).toBe(true)
  })

  it('5 consecutive moves are not a violation yet', () => {
    // B' R F D2 B: 5 moves of the inverse scramble, neighboring moves do not match.
    expect(derived("R D B' R F D2 B D")).toBe(false)
  })

  it('rotations and wide turns do not hide the inverse scramble', () => {
    // "B' R F D2 B U2" after y: B→R, R→F, F→L, L→B.
    expect(derived("y R' F L D2 R U2")).toBe(true)
    // "F L' U B' R F": Rw' = L' x', after x' the former B is on top and the former U in front.
    expect(derived("F Rw' F U' R D")).toBe(true)
  })

  it('a regular solution is not considered derived from the scramble', () => {
    expect(derived("D' R2 U F2 L' B U' R D2 F' L2 U2 B")).toBe(false)
  })
})

describe('checkSolution and the scramble', () => {
  it('a solution from the inverse scramble is DNF even though the cube is solved', async () => {
    expect(await checkSolution(SCRAMBLE, INVERSE)).toEqual({ dnf: 'scramble_derived' })
  })
})

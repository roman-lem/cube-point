// FMC solution check: parsing the notation, counting moves and solving a virtual
// cube with cubing.js. Rules: "FMC" in docs/ARCHITECTURE.md.

import { isScrambleDerived } from './scrambleDerived'

/** A longer solution is DNF (WCA regulations). */
export const MAX_FMC_MOVES = 80

/** Why the solution does not count. */
export type FmcDnfReason =
  | 'empty'
  | 'invalid'
  | 'slice'
  | 'too_long'
  | 'scramble_derived'
  | 'not_solved'

/** DNF reason for the participant. */
export const FMC_DNF_REASONS: Record<FmcDnfReason, string> = {
  empty: 'Решение пустое',
  invalid: 'В решении есть недопустимые ходы',
  slice: 'Повороты средних слоёв (M, E, S) запрещены',
  too_long: 'Решение длиннее 80 ходов',
  scramble_derived: 'В решении есть обратный скрамбл или его часть — это запрещено регламентом',
  not_solved: 'Решение не собирает куб',
}

/** Check outcome: a move count, or DNF with a reason. */
export type FmcCheck = { moves: number } | { dnf: FmcDnfReason }

// A face (with w, a wide turn), a rotation or a slice, then a modifier.
const MOVE_RE = /^(?:([RLUDFB]w?)|([xyz])|([MES]))(['2])?$/

/** Solution moves from space-separated notation. */
export function parseSolution(text: string): string[] {
  return text.split(/\s+/).filter(Boolean)
}

/** Move count: faces and wide turns count 1 each, doubles included; rotations count 0. */
export function countMoves(moves: string[]): number {
  return moves.filter((move) => MOVE_RE.exec(move)?.[1]).length
}

/**
 * Checks the solution: no slices, not longer than the limit, not derived from the scramble,
 * and it solves the cube from the scrambled state (a cube counts as solved
 * in any orientation).
 */
export async function checkSolution(scramble: string, solution: string): Promise<FmcCheck> {
  const moves = parseSolution(solution)
  if (moves.length === 0) {
    return { dnf: 'empty' }
  }
  const parsed = moves.map((move) => MOVE_RE.exec(move))
  if (parsed.some((match) => match === null)) {
    return { dnf: 'invalid' }
  }
  if (parsed.some((match) => match![3])) {
    return { dnf: 'slice' }
  }
  const count = countMoves(moves)
  if (count > MAX_FMC_MOVES) {
    return { dnf: 'too_long' }
  }
  if (isScrambleDerived(parseSolution(scramble), moves)) {
    return { dnf: 'scramble_derived' }
  }

  const kpuzzle = await loadCube()
  const solved = kpuzzle
    .defaultPattern()
    .applyAlg(scramble)
    .applyAlg(moves.join(' '))
    .experimentalIsSolved({ ignorePuzzleOrientation: true, ignoreCenterOrientation: true })
  return solved ? { moves: count } : { dnf: 'not_solved' }
}

// cubing.js is large, so it is loaded on the first check or in advance
// via preloadSolutionCheck (during the attempt, so submission does not wait for the network).
let cube: ReturnType<typeof importCube> | null = null

async function importCube() {
  const { cube3x3x3 } = await import('cubing/puzzles')
  return cube3x3x3.kpuzzle()
}

function loadCube() {
  cube ??= importCube().catch((e) => {
    cube = null // on a network error, try again at submission
    throw e
  })
  return cube
}

/** Loads cubing.js for the solution check in advance. */
export function preloadSolutionCheck(): void {
  loadCube().catch(() => {})
}

// Проверка решения FMC: разбор записи, подсчёт ходов и сборка на виртуальном
// кубе через cubing.js. Правила — раздел «FMC» в CLAUDE.md.

import { isScrambleDerived } from './scrambleDerived'

/** Решение длиннее — DNF (регламент WCA). */
export const MAX_FMC_MOVES = 80

/** Почему решение не засчитано. */
export type FmcDnfReason =
  | 'empty'
  | 'invalid'
  | 'slice'
  | 'too_long'
  | 'scramble_derived'
  | 'not_solved'

/** Причина DNF для участника. */
export const FMC_DNF_REASONS: Record<FmcDnfReason, string> = {
  empty: 'Решение пустое',
  invalid: 'В решении есть недопустимые ходы',
  slice: 'Повороты средних слоёв (M, E, S) запрещены',
  too_long: 'Решение длиннее 80 ходов',
  scramble_derived: 'В решении есть обратный скрамбл или его часть — это запрещено регламентом',
  not_solved: 'Решение не собирает куб',
}

/** Итог проверки: число ходов или DNF с причиной. */
export type FmcCheck = { moves: number } | { dnf: FmcDnfReason }

// Грань (с w — широкий поворот), перехват или срез, затем модификатор.
const MOVE_RE = /^(?:([RLUDFB]w?)|([xyz])|([MES]))(['2])?$/

/** Ходы решения из записи через пробелы. */
export function parseSolution(text: string): string[] {
  return text.split(/\s+/).filter(Boolean)
}

/** Число ходов: грани и широкие повороты по 1, включая двойные, перехваты — 0. */
export function countMoves(moves: string[]): number {
  return moves.filter((move) => MOVE_RE.exec(move)?.[1]).length
}

/**
 * Проверяет решение: без срезов, не длиннее лимита, не получено из скрамбла
 * и собирает куб из состояния после скрамбла (собранным считается куб
 * в любой ориентации).
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

// cubing.js большой, поэтому подгружается при первой проверке или заранее
// через preloadSolutionCheck (во время попытки, чтобы сдача не ждала сеть).
let cube: ReturnType<typeof importCube> | null = null

async function importCube() {
  const { cube3x3x3 } = await import('cubing/puzzles')
  return cube3x3x3.kpuzzle()
}

function loadCube() {
  cube ??= importCube().catch((e) => {
    cube = null // при ошибке сети попробуем снова при сдаче
    throw e
  })
  return cube
}

/** Заранее загружает cubing.js для проверки решения. */
export function preloadSolutionCheck(): void {
  loadCube().catch(() => {})
}

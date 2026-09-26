// Editing an FMC solution from the keyboard: a list of moves like R, Rw', x2.

export const FACES = ['R', 'L', 'U', 'D', 'F', 'B'] as const
export const ROTATIONS = ['x', 'y', 'z'] as const
export type Modifier = "'" | '2'

type Base = (typeof FACES)[number] | (typeof ROTATIONS)[number]

/** Adds a move. wide means a wide turn, it does not apply to rotations. */
export function addMove(moves: string[], base: Base, wide: boolean): string[] {
  const isFace = (FACES as readonly string[]).includes(base)
  return [...moves, isFace && wide ? `${base}w` : base]
}

/**
 * Modifier of the last move: replaces the previous one,
 * and pressing the same modifier again removes it.
 */
export function setModifier(moves: string[], modifier: Modifier): string[] {
  if (moves.length === 0) {
    return moves
  }
  const last = moves[moves.length - 1]!
  const base = last.replace(/['2]$/, '')
  const next = last.endsWith(modifier) ? base : base + modifier
  return [...moves.slice(0, -1), next]
}

/** Removes the last move. */
export function removeLast(moves: string[]): string[] {
  return moves.slice(0, -1)
}

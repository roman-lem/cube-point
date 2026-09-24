// Редактирование решения FMC с клавиатуры: список ходов вида R, Rw', x2.

export const FACES = ['R', 'L', 'U', 'D', 'F', 'B'] as const
export const ROTATIONS = ['x', 'y', 'z'] as const
export type Modifier = "'" | '2'

type Base = (typeof FACES)[number] | (typeof ROTATIONS)[number]

/** Добавляет ход. wide — широкий поворот, к перехватам не применяется. */
export function addMove(moves: string[], base: Base, wide: boolean): string[] {
  const isFace = (FACES as readonly string[]).includes(base)
  return [...moves, isFace && wide ? `${base}w` : base]
}

/**
 * Модификатор последнего хода: ставит его вместо прежнего,
 * а повторное нажатие того же модификатора снимает.
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

/** Удаляет последний ход. */
export function removeLast(moves: string[]): string[] {
  return moves.slice(0, -1)
}

// Защита от решения, полученного из скрамбла (запрещено регламентом WCA).
//
// Автоматически ловим только очевидное: в решении есть подряд идущие ходы,
// совпадающие с частью обратного скрамбла длиной от SCRAMBLE_MATCH_MOVES.
// Перехваты и широкие повороты не спасают: решение сначала переводится
// в повороты граней в исходной ориентации куба.

/** С какой длины совпадение с обратным скрамблом считается нарушением. */
export const SCRAMBLE_MATCH_MOVES = 6

type Face = 'R' | 'L' | 'U' | 'D' | 'F' | 'B'
type Rotation = 'x' | 'y' | 'z'
/** Какая грань в исходной ориентации сейчас стоит на каждом месте. */
type Orientation = Record<Face, Face>

// Куда уходит грань при перехвате по часовой стрелке: x как R, y как U, z как F.
// После x на месте U оказывается бывшая F и т. д.
const ROTATION_CYCLES: Record<Rotation, [Face, Face, Face, Face]> = {
  x: ['F', 'U', 'B', 'D'],
  y: ['R', 'F', 'L', 'B'],
  z: ['U', 'R', 'D', 'L'],
}

// Широкий поворот = поворот противоположной грани и перехват: Rw = L x, Lw = R x'.
// Третье значение — направление перехвата.
const WIDE: Record<Face, [Face, Rotation, string]> = {
  R: ['L', 'x', ''],
  L: ['R', 'x', "'"],
  U: ['D', 'y', ''],
  D: ['U', 'y', "'"],
  F: ['B', 'z', ''],
  B: ['F', 'z', "'"],
}

const MOVE_RE = /^(?:([RLUDFB])(w)?|([xyz]))(['2])?$/

/** Сколько четвертей по часовой: '' → 1, 2 → 2, ' → 3. */
function turns(modifier: string): number {
  return modifier === '2' ? 2 : modifier === "'" ? 3 : 1
}

function rotate(orientation: Orientation, rotation: Rotation, quarterTurns: number): Orientation {
  let result = orientation
  const [a, b, c, d] = ROTATION_CYCLES[rotation]
  for (let i = 0; i < quarterTurns; i++) {
    // Грань с места a переезжает на место b и т. д.
    result = { ...result, [b]: result[a], [c]: result[b], [d]: result[c], [a]: result[d] }
  }
  return result
}

function combine(modifier: string, extra: string): string {
  const total = (turns(modifier) * (extra === "'" ? 3 : 1)) % 4
  return total === 2 ? '2' : total === 3 ? "'" : ''
}

/**
 * Повороты граней в исходной ориентации куба, без перехватов.
 * Ходы, которые не удалось разобрать, пропускаются: их отсекает checkSolution.
 */
export function toFaceTurns(moves: string[]): string[] {
  let orientation: Orientation = { R: 'R', L: 'L', U: 'U', D: 'D', F: 'F', B: 'B' }
  const result: string[] = []
  for (const move of moves) {
    const match = MOVE_RE.exec(move)
    if (!match) continue
    const [, face, wide, rotation, modifier = ''] = match
    if (rotation) {
      orientation = rotate(orientation, rotation as Rotation, turns(modifier))
    } else if (wide) {
      const [opposite, wideRotation, direction] = WIDE[face as Face]
      result.push(orientation[opposite] + modifier)
      orientation = rotate(orientation, wideRotation, turns(combine(modifier, direction)))
    } else {
      result.push(orientation[face as Face] + modifier)
    }
  }
  return result
}

function invert(move: string): string {
  if (move.endsWith('2')) return move
  return move.endsWith("'") ? move.slice(0, -1) : `${move}'`
}

/** Есть ли в решении SCRAMBLE_MATCH_MOVES ходов подряд из обратного скрамбла. */
export function isScrambleDerived(scramble: string[], solution: string[]): boolean {
  const inverse = toFaceTurns(scramble).reverse().map(invert)
  const turnsInSolution = toFaceTurns(solution)
  const n = SCRAMBLE_MATCH_MOVES
  const solutionWindows = new Set<string>()
  for (let i = 0; i + n <= turnsInSolution.length; i++) {
    solutionWindows.add(turnsInSolution.slice(i, i + n).join(' '))
  }
  for (let i = 0; i + n <= inverse.length; i++) {
    if (solutionWindows.has(inverse.slice(i, i + n).join(' '))) {
      return true
    }
  }
  return false
}

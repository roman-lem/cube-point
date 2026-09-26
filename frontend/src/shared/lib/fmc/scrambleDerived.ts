// Protection against a solution derived from the scramble (forbidden by the WCA regulations).
//
// Only the obvious is caught automatically: the solution contains consecutive moves
// matching a part of the inverse scramble at least SCRAMBLE_MATCH_MOVES long.
// Rotations and wide turns do not help: the solution is first converted
// to face turns in the cube's original orientation.

/** Match length with the inverse scramble from which it counts as a violation. */
export const SCRAMBLE_MATCH_MOVES = 6

type Face = 'R' | 'L' | 'U' | 'D' | 'F' | 'B'
type Rotation = 'x' | 'y' | 'z'
/** Which face of the original orientation is now in each position. */
type Orientation = Record<Face, Face>

// Where a face goes on a clockwise rotation: x like R, y like U, z like F.
// After x the former F is in the U position, and so on.
const ROTATION_CYCLES: Record<Rotation, [Face, Face, Face, Face]> = {
  x: ['F', 'U', 'B', 'D'],
  y: ['R', 'F', 'L', 'B'],
  z: ['U', 'R', 'D', 'L'],
}

// A wide turn = a turn of the opposite face plus a rotation: Rw = L x, Lw = R x'.
// The third value is the rotation direction.
const WIDE: Record<Face, [Face, Rotation, string]> = {
  R: ['L', 'x', ''],
  L: ['R', 'x', "'"],
  U: ['D', 'y', ''],
  D: ['U', 'y', "'"],
  F: ['B', 'z', ''],
  B: ['F', 'z', "'"],
}

const MOVE_RE = /^(?:([RLUDFB])(w)?|([xyz]))(['2])?$/

/** How many clockwise quarter turns: '' → 1, 2 → 2, ' → 3. */
function turns(modifier: string): number {
  return modifier === '2' ? 2 : modifier === "'" ? 3 : 1
}

function rotate(orientation: Orientation, rotation: Rotation, quarterTurns: number): Orientation {
  let result = orientation
  const [a, b, c, d] = ROTATION_CYCLES[rotation]
  for (let i = 0; i < quarterTurns; i++) {
    // The face from position a moves to position b, and so on.
    result = { ...result, [b]: result[a], [c]: result[b], [d]: result[c], [a]: result[d] }
  }
  return result
}

function combine(modifier: string, extra: string): string {
  const total = (turns(modifier) * (extra === "'" ? 3 : 1)) % 4
  return total === 2 ? '2' : total === 3 ? "'" : ''
}

/**
 * Face turns in the cube's original orientation, without rotations.
 * Moves that could not be parsed are skipped: checkSolution rejects them.
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

/** Whether the solution has SCRAMBLE_MATCH_MOVES consecutive moves from the inverse scramble. */
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

/**
 * A random scramble for an event via cubing.js.
 *
 * cubing.js is large, so it is loaded on the first call and generates
 * scrambles in a web worker. The app's scrambles are not official.
 */
export async function randomScramble(eventId: string): Promise<string> {
  const { randomScrambleForEvent } = await import('cubing/scramble')
  return (await randomScrambleForEvent(eventId)).toString()
}

/**
 * Scramble lines for display and printing. The server stores a scramble in one line;
 * a megaminx scramble is split as usual: a line ends with U or U' (7 lines).
 * Other events are one line.
 */
export function scrambleLines(eventId: string, scramble: string): string[] {
  const moves = scramble.split(/\s+/).filter(Boolean)
  if (eventId !== 'minx') {
    return [moves.join(' ')]
  }
  const lines: string[][] = [[]]
  for (const move of moves) {
    lines[lines.length - 1]!.push(move)
    if (move === 'U' || move === "U'") {
      lines.push([])
    }
  }
  return lines.filter((line) => line.length > 0).map((line) => line.join(' '))
}

/**
 * Pieces of a scramble line between which it can wrap. A Square-1 line wraps
 * only right after "/", so a piece is "(1, -3) /"; other events wrap between moves.
 */
export function scramblePieces(eventId: string, line: string): string[] {
  return line.split(eventId === 'sq1' ? /(?<=\/)\s+/ : /\s+/).filter(Boolean)
}

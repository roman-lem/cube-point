import { ATTEMPTS_COUNT, randomScramble, type SeriesFormat } from '@/shared/lib'

/**
 * Scrambles for the meetup events: one for each attempt of the format.
 * onProgress(done, total).
 */
export async function generateScrambles(
  events: { eventId: string; format: SeriesFormat }[],
  onProgress: (done: number, total: number) => void,
): Promise<string[][]> {
  const total = events.reduce((sum, e) => sum + ATTEMPTS_COUNT[e.format], 0)
  let done = 0
  onProgress(done, total)

  const result: string[][] = []
  for (const { eventId, format } of events) {
    const scrambles: string[] = []
    for (let i = 0; i < ATTEMPTS_COUNT[format]; i++) {
      scrambles.push(await randomScramble(eventId))
      onProgress(++done, total)
    }
    result.push(scrambles)
  }
  return result
}

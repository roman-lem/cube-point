import { ATTEMPTS_COUNT, type SeriesFormat } from '@/shared/lib'

/**
 * Скрамблы для дисциплин встречи: по одному на каждую попытку формата.
 *
 * cubing.js подгружается только здесь (он большой и нужен лишь при создании
 * встречи) и генерирует скрамблы в web worker. onProgress(готово, всего).
 */
export async function generateScrambles(
  events: { eventId: string; format: SeriesFormat }[],
  onProgress: (done: number, total: number) => void,
): Promise<string[][]> {
  const { randomScrambleForEvent } = await import('cubing/scramble')
  const total = events.reduce((sum, e) => sum + ATTEMPTS_COUNT[e.format], 0)
  let done = 0
  onProgress(done, total)

  const result: string[][] = []
  for (const { eventId, format } of events) {
    const scrambles: string[] = []
    for (let i = 0; i < ATTEMPTS_COUNT[format]; i++) {
      scrambles.push((await randomScrambleForEvent(eventId)).toString())
      onProgress(++done, total)
    }
    result.push(scrambles)
  }
  return result
}

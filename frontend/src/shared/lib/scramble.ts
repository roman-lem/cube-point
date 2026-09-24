/**
 * Случайный скрамбл дисциплины через cubing.js.
 *
 * cubing.js большой, поэтому подгружается при первом вызове, а скрамблы
 * генерирует в web worker. Скрамблы приложения не официальные.
 */
export async function randomScramble(eventId: string): Promise<string> {
  const { randomScrambleForEvent } = await import('cubing/scramble')
  return (await randomScrambleForEvent(eventId)).toString()
}

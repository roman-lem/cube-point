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

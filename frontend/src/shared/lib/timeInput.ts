import { MAX_TIME } from './results'

/**
 * Time from manual input in hundredths of a second, or null if the input is invalid.
 *
 * Understands:
 * - "9.87", "9,87", "12.3" (one digit after the point means tenths), "1:02.45", "1:05:23.45";
 * - digits only, the last two are hundredths, then seconds, minutes and hours by two digits:
 *   "987" → 9.87, "10245" → 1:02.45, "234567" → 23:45.67, "1052345" → 1:05:23.45.
 *
 * If a larger unit is given, a smaller one is at most 59: "1:75.00" is a typo.
 * The largest given unit is not limited ("75.5" is 1:15.50), only the time is below MAX_TIME.
 */
export function parseTimeInput(text: string): number | null {
  const input = text.trim().replace(',', '.')
  let hours: number
  let minutes: number
  let seconds: number
  let hundredths: number

  const digitsOnly = /^\d{1,7}$/.exec(input)
  const withDot = /^(?:(?:(\d{1,2}):)?(\d{1,3}):)?(\d+)(?:\.(\d{1,2}))?$/.exec(input)

  if (digitsOnly) {
    // As in csTimer: 10245 = 1:02.45.
    const padded = input.padStart(7, '0')
    hours = Number(padded.slice(0, 1))
    minutes = Number(padded.slice(1, 3))
    seconds = Number(padded.slice(3, 5))
    hundredths = Number(padded.slice(5))
  } else if (withDot) {
    const [, h, m, s, cs] = withDot
    // After a colon the unit is written with two digits: "1:5.00" and "1:5:00" are typos.
    if ((m && s!.length !== 2) || (h && m!.length !== 2)) {
      return null
    }
    hours = h ? Number(h) : 0
    minutes = m ? Number(m) : 0
    seconds = Number(s)
    hundredths = cs ? Number(cs.padEnd(2, '0')) : 0
  } else {
    return null
  }

  if ((hours > 0 && minutes > 59) || ((hours > 0 || minutes > 0) && seconds > 59)) {
    return null
  }
  const value = hours * 360000 + minutes * 6000 + seconds * 100 + hundredths
  return value > 0 && value < MAX_TIME ? value : null
}

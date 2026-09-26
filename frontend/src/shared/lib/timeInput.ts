/**
 * Time from manual input in hundredths of a second, or null if the input is invalid.
 *
 * Understands:
 * - "9.87", "9,87", "12.3" (one digit after the point means tenths), "1:02.45";
 * - digits only, the last two are hundredths: "987" → 9.87, "10245" → 1:02.45.
 */
export function parseTimeInput(text: string): number | null {
  const input = text.trim().replace(',', '.')
  let minutes = 0
  let seconds: number
  let hundredths: number

  const digitsOnly = /^\d{1,7}$/.exec(input)
  const withDot = /^(?:(\d{1,3}):)?(\d+)(?:\.(\d{1,2}))?$/.exec(input)

  if (digitsOnly) {
    // As in csTimer: 10245 = 1:02.45. Seconds are the two digits before the hundredths.
    const padded = input.padStart(5, '0')
    minutes = Number(padded.slice(0, -4))
    seconds = Number(padded.slice(-4, -2))
    hundredths = Number(padded.slice(-2))
  } else if (withDot) {
    minutes = withDot[1] ? Number(withDot[1]) : 0
    seconds = Number(withDot[2])
    hundredths = withDot[3] ? Number(withDot[3].padEnd(2, '0')) : 0
    // With minutes, seconds are at most 59: "1:75" is a typo.
    if (withDot[1] && withDot[2]!.length !== 2) {
      return null
    }
  } else {
    return null
  }

  if (minutes > 0 && seconds > 59) {
    return null
  }
  const value = minutes * 6000 + seconds * 100 + hundredths
  return value > 0 ? value : null
}

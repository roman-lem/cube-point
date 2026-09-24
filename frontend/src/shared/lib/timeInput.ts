/**
 * Время из ручного ввода в сотых долях секунды или null, если ввод неверный.
 *
 * Понимает:
 * - «9.87», «9,87», «12.3» (одна цифра после точки — десятые), «1:02.45»;
 * - только цифры, последние две — сотые: «987» → 9.87, «10245» → 1:02.45.
 */
export function parseTimeInput(text: string): number | null {
  const input = text.trim().replace(',', '.')
  let minutes = 0
  let seconds: number
  let hundredths: number

  const digitsOnly = /^\d{1,7}$/.exec(input)
  const withDot = /^(?:(\d{1,3}):)?(\d+)(?:\.(\d{1,2}))?$/.exec(input)

  if (digitsOnly) {
    // Как в csTimer: 10245 = 1:02.45. Секунды — две цифры перед сотыми.
    const padded = input.padStart(5, '0')
    minutes = Number(padded.slice(0, -4))
    seconds = Number(padded.slice(-4, -2))
    hundredths = Number(padded.slice(-2))
  } else if (withDot) {
    minutes = withDot[1] ? Number(withDot[1]) : 0
    seconds = Number(withDot[2])
    hundredths = withDot[3] ? Number(withDot[3].padEnd(2, '0')) : 0
    // С минутами секунды не больше 59: «1:75» — опечатка.
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

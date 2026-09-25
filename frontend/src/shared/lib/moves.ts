import { pluralForm } from './plural'

/** Слово к числу ходов FMC: 25 → «ходов», 21 → «ход»; среднее (25.33) — «хода». */
export function movesWord(value: number, isAverage = false): string {
  return isAverage ? 'хода' : pluralForm(value, ['ход', 'хода', 'ходов'])
}

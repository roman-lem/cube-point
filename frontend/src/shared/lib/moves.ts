import { pluralForm } from './plural'

/** Word for an FMC move count: 25 → «ходов», 21 → «ход»; a mean (25.33) → «хода». */
export function movesWord(value: number, isAverage = false): string {
  return isAverage ? 'хода' : pluralForm(value, ['ход', 'хода', 'ходов'])
}

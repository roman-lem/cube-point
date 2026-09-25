import { MAX_FMC_MOVES, formatResult, parseTimeInput, type Attempt, type ResultType } from '@/shared/lib'

// Ручной ввод попытки организатором — одной строкой, как в электронной таблице:
// «1234» → 12.34, «10234» → 1:02.34, «1234+» → 12.34 (+2), «d» или «dnf» → DNF,
// «1234 d» → DNF с сохранённым временем, «dns» → DNS. В FMC — число ходов.

const SUFFIXES: Record<string, Attempt['penalty']> = {
  '': 'none',
  '+': 'plus2',
  '+2': 'plus2',
  d: 'dnf',
  dnf: 'dnf',
  dns: 'dns',
}

const INPUT_RE = /^([\d:.,]*)\s*(\+2?|dnf|dns|d)?$/i

/** Попытка из введённого текста или null, если ввод не понят. Пустой текст — тоже null. */
export function parseAttemptText(text: string, resultType: ResultType): Attempt | null {
  const match = INPUT_RE.exec(text.trim())
  if (!match) {
    return null
  }
  const number = match[1] ?? ''
  const penalty = SUFFIXES[(match[2] ?? '').toLowerCase()]!
  let value: number | null = null
  if (number) {
    value = resultType === 'moves' ? parseMoves(number) : parseTimeInput(number)
    if (value === null) {
      return null
    }
  }
  if (value === null && (penalty === 'none' || penalty === 'plus2')) {
    return null
  }
  if (penalty === 'plus2' && resultType === 'moves') {
    return null
  }
  return { value, penalty }
}

function parseMoves(text: string): number | null {
  if (!/^\d+$/.test(text)) {
    return null
  }
  const moves = Number(text)
  return moves >= 1 && moves <= MAX_FMC_MOVES ? moves : null
}

/** Текст попытки для редактирования; parseAttemptText разбирает его обратно. */
export function attemptToText(attempt: Attempt | null, resultType: ResultType): string {
  if (!attempt) {
    return ''
  }
  const value = attempt.value === null ? '' : formatResult(attempt.value, resultType)
  const suffix = { none: '', plus2: '+', dnf: ' DNF', dns: ' DNS' }[attempt.penalty]
  return `${value}${suffix}`.trim()
}

export function sameAttempt(a: Attempt | null, b: Attempt | null): boolean {
  return a?.value === b?.value && a?.penalty === b?.penalty
}

/** «+» и кнопка +2: включает и выключает штраф. Без времени — null. */
export function togglePlus2(attempt: Attempt | null): Attempt | null {
  if (attempt?.value == null) {
    return null
  }
  return { value: attempt.value, penalty: attempt.penalty === 'plus2' ? 'none' : 'plus2' }
}

/**
 * «d» и кнопка DNF: ставит DNF, время остаётся. Повторно — снимает DNF,
 * если время есть (иначе снимать нечего — null).
 */
export function toggleDnf(attempt: Attempt | null): Attempt | null {
  if (attempt?.penalty === 'dnf') {
    return attempt.value === null ? null : { value: attempt.value, penalty: 'none' }
  }
  return { value: attempt?.value ?? null, penalty: 'dnf' }
}

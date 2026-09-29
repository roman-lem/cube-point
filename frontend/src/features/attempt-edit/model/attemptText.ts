import { MAX_FMC_MOVES, formatResult, parseTimeInput, type Attempt, type ResultType } from '@/shared/lib'

// An organizer enters an attempt as a single line, like in a spreadsheet:
// "1234" → 12.34, "10234" → 1:02.34, "1234+" → 12.34 (+2), "d" or "dnf" → DNF,
// "1234 d" → DNF with the time kept, "dns" → DNS. In FMC it is a move count.

const SUFFIXES: Record<string, Attempt['penalty']> = {
  '': 'none',
  '+': 'plus2',
  '+2': 'plus2',
  d: 'dnf',
  dnf: 'dnf',
  dns: 'dns',
}

const INPUT_RE = /^([\d:.,]*)\s*(\+2?|dnf|dns|d)?$/i

/** The attempt from the entered text, or null if the input is not understood. Empty text is null too. */
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

/** Attempt text for editing; parseAttemptText parses it back. */
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

/** "+" and the +2 button: toggles the penalty. Without a time, null. */
export function togglePlus2(attempt: Attempt | null): Attempt | null {
  if (attempt?.value == null) {
    return null
  }
  return { value: attempt.value, penalty: attempt.penalty === 'plus2' ? 'none' : 'plus2' }
}

/**
 * "d" and the DNF button: sets DNF, the time stays. Again: removes DNF
 * if there is a time (otherwise there is nothing to remove, null).
 */
export function toggleDnf(attempt: Attempt | null): Attempt | null {
  if (attempt?.penalty === 'dnf') {
    return attempt.value === null ? null : { value: attempt.value, penalty: 'none' }
  }
  return { value: attempt?.value ?? null, penalty: 'dnf' }
}

/**
 * FMC: the organizer does not enter moves, only replaces a result with DNF
 * (the moves stay, so the original result can be restored). null: nothing to replace.
 */
export function fmcDnf(attempt: Attempt | null): Attempt | null {
  return attempt?.penalty === 'none' ? { value: attempt.value, penalty: 'dnf' } : null
}

/** The attempt differs from its original result: "Restore original" makes sense. */
export function canRestore(attempt: (Attempt & { edited?: boolean; original?: Attempt }) | null) {
  return Boolean(attempt?.edited && attempt.original && !sameAttempt(attempt, attempt.original))
}

// Series results, training averages and formatting for display.
//
// Repeats backend/app/results.py (the source of truth) for live recalculation
// while typing. Both implementations are checked by the shared cases in
// testdata/results_cases.json.
//
// Time is an integer in hundredths of a second, FMC is a number of moves.
// The FMC mean is in hundredths of a move.

export type Penalty = 'none' | 'plus2' | 'dnf' | 'dns'
export type ResultType = 'time' | 'moves'
export type SeriesFormat = 'ao5' | 'mo3' | 'bo5' | 'bo3' | 'bo1'

export interface Attempt {
  value: number | null
  penalty: Penalty
}

export interface SeriesResult {
  /** Best of the entered attempts, DNF, or null if there are no attempts. */
  best: number | null
  /** Average for ao5 and mo3, DNF, or null while the series is unfinished. Always null for bo formats. */
  average: number | null
  /** A flag for each attempt of the format: false for the ones dropped in ao5. All true while the series is unfinished. */
  counting: boolean[]
}

/** DNF result (of an attempt or a series). DNS also gives DNF in calculations. */
export const DNF = -1

export const ATTEMPTS_COUNT: Record<SeriesFormat, number> = {
  ao5: 5,
  mo3: 3,
  bo5: 5,
  bo3: 3,
  bo1: 1,
}

const PENALTIES: Penalty[] = ['none', 'plus2', 'dnf', 'dns']
const RESULT_TYPES: ResultType[] = ['time', 'moves']

const PLUS_TWO = 200 // +2 seconds in hundredths

/** Time limit: less than three hours. Mirror of MAX_VALUE in backend/app/series.py. */
export const MAX_TIME = 1_080_000

/** Final value of an attempt: with the +2 penalty, or DNF. */
export function attemptValue(attempt: Attempt, resultType: ResultType): number {
  checkAttempt(attempt, resultType)
  if (attempt.penalty === 'dnf' || attempt.penalty === 'dns') {
    return DNF
  }
  if (attempt.penalty === 'plus2') {
    return attempt.value! + PLUS_TWO
  }
  return attempt.value!
}

/**
 * Best result, average and counting attempts of a series.
 * attempts are in order, no more than the format's number of attempts.
 * An attempt not yet done is null or missing at the end of the list.
 */
export function calcSeries(
  attempts: (Attempt | null)[],
  seriesFormat: SeriesFormat,
  resultType: ResultType,
): SeriesResult {
  if (!Object.hasOwn(ATTEMPTS_COUNT, seriesFormat)) {
    throw new Error(`Неизвестный формат: ${seriesFormat}`)
  }
  checkResultType(resultType)
  const count = ATTEMPTS_COUNT[seriesFormat]
  if (attempts.length > count) {
    throw new Error(`В формате ${seriesFormat} не больше ${count} попыток`)
  }

  const values = attempts
    .filter((a): a is Attempt => a !== null)
    .map((a) => attemptValue(a, resultType))
  const isComplete = values.length === count
  const dnfCount = values.filter((v) => v === DNF).length

  let average: number | null = null
  let counting: boolean[] = new Array(count).fill(true)

  if (seriesFormat === 'ao5') {
    // Two DNFs make the average DNF right away, even if the series is unfinished.
    // The remaining attempts can still be done.
    if (dnfCount >= 2) {
      average = DNF
    }
    if (isComplete) {
      // Stable sort: on ties the first of the best
      // and the last of the worst are dropped.
      const order = [...values.keys()].sort((a, b) => compareValues(values[a]!, values[b]!))
      const dropped = [order[0], order[order.length - 1]]
      counting = values.map((_, i) => !dropped.includes(i))
      average = trimmedMean(values, resultType)
    }
  } else if (seriesFormat === 'mo3') {
    if (dnfCount >= 1) {
      average = DNF
    } else if (isComplete) {
      average = mean(values, resultType)
    }
  }

  return { best: best(values), average, counting }
}

/**
 * Average of the last n attempts (training ao5, ao12), or null if there are fewer than n.
 * One best and one worst attempt are dropped, the rest are averaged.
 * One DNF is dropped as the worst; two or more make the average DNF.
 */
export function averageOf(attempts: Attempt[], n: number, resultType: ResultType): number | null {
  checkWindow(n)
  checkResultType(resultType)
  if (attempts.length < n) {
    return null
  }
  return trimmedMean(attempts.slice(-n).map((a) => attemptValue(a, resultType)), resultType)
}

/**
 * Rolling averages: for each attempt, the average of the n attempts
 * ending with it (as averageOf). The first n - 1 attempts get null.
 */
export function rollingAverages(
  attempts: Attempt[],
  n: number,
  resultType: ResultType,
): (number | null)[] {
  checkWindow(n)
  checkResultType(resultType)
  const values = attempts.map((a) => attemptValue(a, resultType))
  return values.map((_, i) =>
    i + 1 >= n ? trimmedMean(values.slice(i + 1 - n, i + 1), resultType) : null,
  )
}

/** Result for display: 9.87, 1:02.45, 1:05:23.45, 28, 28.33, DNF, —. */
export function formatResult(
  value: number | null,
  resultType: ResultType,
  isAverage = false,
): string {
  checkResultType(resultType)
  if (value === null) {
    return '—'
  }
  if (value === DNF) {
    return 'DNF'
  }
  if (resultType === 'moves') {
    if (isAverage) {
      return `${Math.floor(value / 100)}.${pad2(value % 100)}`
    }
    return String(value)
  }
  return formatTime(value)
}

/** Attempt for display: 9.87, 11.87 (+2), DNF, DNS, —. */
export function formatAttempt(attempt: Attempt | null, resultType: ResultType): string {
  if (attempt === null) {
    return '—'
  }
  const value = attemptValue(attempt, resultType)
  if (attempt.penalty === 'dns') {
    return 'DNS'
  }
  let text = formatResult(value, resultType)
  if (attempt.penalty === 'plus2') {
    text += ' (+2)'
  }
  return text
}

function checkResultType(resultType: ResultType): void {
  if (!RESULT_TYPES.includes(resultType)) {
    throw new Error(`Неизвестный тип результата: ${resultType}`)
  }
}

function checkAttempt(attempt: Attempt, resultType: ResultType): void {
  const { penalty, value } = attempt
  if (!PENALTIES.includes(penalty)) {
    throw new Error(`Неизвестный штраф: ${penalty}`)
  }
  if (penalty === 'plus2' && resultType === 'moves') {
    throw new Error('В FMC нет штрафа +2')
  }
  if (value === null) {
    if (penalty === 'none' || penalty === 'plus2') {
      throw new Error('У попытки без DNF/DNS должно быть значение')
    }
    return
  }
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`Значение попытки должно быть целым больше нуля: ${value}`)
  }
}

// Fewer than three attempts: nothing left to average after dropping the best and worst.
function checkWindow(n: number): void {
  if (!Number.isInteger(n) || n < 3) {
    throw new Error(`Число попыток для среднего должно быть не меньше 3: ${n}`)
  }
}

/** Average without one best and one worst attempt; two or more DNFs give DNF. */
function trimmedMean(values: number[], resultType: ResultType): number {
  if (values.filter((v) => v === DNF).length >= 2) {
    return DNF
  }
  const kept = [...values].sort(compareValues).slice(1, -1)
  return mean(kept, resultType)
}

// DNF is worse than any time.
function compareValues(a: number, b: number): number {
  if (a === b) return 0
  if (a === DNF) return 1
  if (b === DNF) return -1
  return a - b
}

function best(values: number[]): number | null {
  const successful = values.filter((v) => v !== DNF)
  if (successful.length > 0) {
    return Math.min(...successful)
  }
  if (values.length > 0) {
    return DNF
  }
  return null
}

function mean(values: number[], resultType: ResultType): number {
  // Round down to hundredths: thousandths are simply dropped.
  let total = values.reduce((sum, v) => sum + v, 0)
  if (resultType === 'moves') {
    total *= 100 // the FMC mean is in hundredths of a move
  }
  return Math.floor(total / values.length)
}

function formatTime(centiseconds: number): string {
  const hours = Math.floor(centiseconds / 360000)
  const minutes = Math.floor((centiseconds % 360000) / 6000)
  const seconds = Math.floor((centiseconds % 6000) / 100)
  const hundredths = centiseconds % 100
  if (hours > 0) {
    return `${hours}:${pad2(minutes)}:${pad2(seconds)}.${pad2(hundredths)}`
  }
  if (minutes > 0) {
    return `${minutes}:${pad2(seconds)}.${pad2(hundredths)}`
  }
  return `${seconds}.${pad2(hundredths)}`
}

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

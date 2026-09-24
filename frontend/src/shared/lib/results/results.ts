// Подсчёт результатов серии, средних тренировки и форматирование для отображения.
//
// Повторяет backend/app/results.py (источник правды) для живого пересчёта
// при вводе. Обе реализации проверяются общими тестами из
// testdata/results_cases.json.
//
// Время — целое число в сотых долях секунды, FMC — число ходов.
// Среднее FMC — в сотых долях хода.

export type Penalty = 'none' | 'plus2' | 'dnf' | 'dns'
export type ResultType = 'time' | 'moves'
export type SeriesFormat = 'ao5' | 'mo3' | 'bo5' | 'bo3' | 'bo1'

export interface Attempt {
  value: number | null
  penalty: Penalty
}

export interface SeriesResult {
  /** Лучшая из введённых попыток, DNF или null, если попыток нет. */
  best: number | null
  /** Среднее для ao5 и mo3, DNF или null, пока серия не закончена. Для bo-форматов всегда null. */
  average: number | null
  /** По флагу на каждую попытку формата: false у отброшенных в ao5. Пока серия не закончена, все true. */
  counting: boolean[]
}

/** Результат DNF (попытки или серии). DNS в подсчёте тоже даёт DNF. */
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

const PLUS_TWO = 200 // +2 секунды в сотых долях

/** Итоговое значение попытки: со штрафом +2 или DNF. */
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
 * Лучший результат, среднее и учитываемые попытки серии.
 * attempts — попытки по порядку, не больше числа попыток формата.
 * Несобранная попытка — null или отсутствует в конце списка.
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
    // Два DNF — среднее DNF сразу, даже если серия не закончена.
    // Остальные попытки при этом всё равно можно дособрать.
    if (dnfCount >= 2) {
      average = DNF
    }
    if (isComplete) {
      // Стабильная сортировка: при равенстве отбрасывается
      // первая из лучших и последняя из худших.
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
 * Среднее последних n попыток (ao5, ao12 тренировки) или null, если их меньше n.
 * Отбрасываются одна лучшая и одна худшая попытка, остальные усредняются.
 * Один DNF отбрасывается как худшая, два и более — среднее DNF.
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
 * Скользящие средние: для каждой попытки — среднее n попыток, которыми
 * она заканчивается (как averageOf). У первых n - 1 попыток — null.
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

/** Результат для отображения: 9.87, 1:02.45, 28, 28.33, DNF, —. */
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

/** Попытка для отображения: 9.87, 11.87 (+2), DNF, DNS, —. */
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

// Меньше трёх попыток: после отбрасывания лучшей и худшей нечего усреднять.
function checkWindow(n: number): void {
  if (!Number.isInteger(n) || n < 3) {
    throw new Error(`Число попыток для среднего должно быть не меньше 3: ${n}`)
  }
}

/** Среднее без одной лучшей и одной худшей попытки; два DNF и более — DNF. */
function trimmedMean(values: number[], resultType: ResultType): number {
  if (values.filter((v) => v === DNF).length >= 2) {
    return DNF
  }
  const kept = [...values].sort(compareValues).slice(1, -1)
  return mean(kept, resultType)
}

// DNF хуже любого времени.
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
  // Округление вниз до сотых: тысячные просто отбрасываются.
  let total = values.reduce((sum, v) => sum + v, 0)
  if (resultType === 'moves') {
    total *= 100 // среднее FMC — в сотых долях хода
  }
  return Math.floor(total / values.length)
}

function formatTime(centiseconds: number): string {
  const minutes = Math.floor(centiseconds / 6000)
  const rest = centiseconds % 6000
  const seconds = Math.floor(rest / 100)
  const hundredths = rest % 100
  if (minutes > 0) {
    return `${minutes}:${pad2(seconds)}.${pad2(hundredths)}`
  }
  return `${seconds}.${pad2(hundredths)}`
}

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

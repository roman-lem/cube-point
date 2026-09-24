// Тренировочная сессия: сборки одной дисциплины, хранятся только в браузере.
// Правила — «Таймер» в CLAUDE.md. Здесь чистые функции без Vue: разбор
// данных из хранилища, изменения сессии и её статистика.
import { DNF, attemptValue, averageOf } from '@/shared/lib'

/** DNS в тренировке нет: его ставит только завершение встречи. */
export type TrainingPenalty = 'none' | 'plus2' | 'dnf'

export interface TrainingSolve {
  /** Время без штрафа в сотых долях секунды. */
  value: number
  penalty: TrainingPenalty
  /** Момент сборки (мс с 1970 года), он же идентификатор сборки в сессии. */
  at: number
}

export interface SessionStats {
  ao5: number | null
  ao12: number | null
  /** Лучшая сборка, DNF, если все DNF, или null, если сборок нет. */
  best: number | null
  count: number
}

/** Версия формата в хранилище. Данные другой версии не читаются. */
export const SESSION_VERSION = 1

const PENALTIES: TrainingPenalty[] = ['none', 'plus2', 'dnf']

/**
 * Сборки из строки хранилища. Никогда не бросает исключений:
 * битые данные или другая версия — пустая сессия, некорректная
 * сборка (или повтор at) выбрасывается, остальные сохраняются.
 */
export function parseSession(raw: string | null): TrainingSolve[] {
  if (!raw) {
    return []
  }
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return []
  }
  if (!isObject(data) || data.version !== SESSION_VERSION || !Array.isArray(data.solves)) {
    return []
  }
  const seen = new Set<number>()
  const solves: TrainingSolve[] = []
  for (const item of data.solves) {
    if (isSolve(item) && !seen.has(item.at)) {
      seen.add(item.at)
      solves.push({ value: item.value, penalty: item.penalty, at: item.at })
    }
  }
  return solves
}

export function serializeSession(solves: TrainingSolve[]): string {
  return JSON.stringify({ version: SESSION_VERSION, solves })
}

/** Новая сборка в конец сессии. at всегда больше, чем у предыдущей. */
export function addSolve(
  solves: TrainingSolve[],
  value: number,
  penalty: TrainingPenalty,
  now = Date.now(),
): TrainingSolve[] {
  const last = solves[solves.length - 1]
  const at = last && last.at >= now ? last.at + 1 : now
  return [...solves, { value, penalty, at }]
}

export function setPenalty(
  solves: TrainingSolve[],
  at: number,
  penalty: TrainingPenalty,
): TrainingSolve[] {
  return solves.map((s) => (s.at === at ? { ...s, penalty } : s))
}

export function removeSolve(solves: TrainingSolve[], at: number): TrainingSolve[] {
  return solves.filter((s) => s.at !== at)
}

export function sessionStats(solves: TrainingSolve[]): SessionStats {
  const values = solves.map((s) => attemptValue(s, 'time'))
  const successful = values.filter((v) => v !== DNF)
  let best: number | null = null
  if (successful.length > 0) {
    best = Math.min(...successful)
  } else if (values.length > 0) {
    best = DNF
  }
  return {
    ao5: averageOf(solves, 5, 'time'),
    ao12: averageOf(solves, 12, 'time'),
    best,
    count: solves.length,
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isSolve(item: unknown): item is TrainingSolve {
  return (
    isObject(item) &&
    Number.isInteger(item.value) &&
    (item.value as number) > 0 &&
    PENALTIES.includes(item.penalty as TrainingPenalty) &&
    Number.isInteger(item.at)
  )
}

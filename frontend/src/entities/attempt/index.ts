// Подсчёт и форматирование живут в shared/lib/results,
// чтобы ими могли пользоваться и attempt, и series.
export { DNF, attemptValue, formatAttempt, formatResult } from '@/shared/lib'
export type { Attempt, Penalty, ResultType } from '@/shared/lib'

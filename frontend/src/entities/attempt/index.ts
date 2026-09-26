// Calculation and formatting live in shared/lib/results
// so that both attempt and series can use them.
export { DNF, attemptValue, formatAttempt, formatResult } from '@/shared/lib'
export type { Attempt, Penalty, ResultType } from '@/shared/lib'
export { default as TimeValue } from './ui/TimeValue.vue'

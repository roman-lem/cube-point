// Подсчёт и форматирование живут в shared/lib/results,
// чтобы ими могли пользоваться и attempt, и series.
export { ATTEMPTS_COUNT, calcSeries } from '@/shared/lib'
export type { SeriesFormat, SeriesResult } from '@/shared/lib'
export { fetchEventResults, fetchMySeries } from './api/seriesApi'
export type {
  EventResults, MySeries, ResultsRow, SavedAttempt, SeriesStatus,
} from './model/types'
export { default as AttemptSeries } from './ui/AttemptSeries.vue'
export { default as ResultRow } from './ui/ResultRow.vue'

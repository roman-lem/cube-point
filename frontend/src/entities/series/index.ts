// Calculation and formatting live in shared/lib/results
// so that both attempt and series can use them.
export { ATTEMPTS_COUNT, calcSeries } from '@/shared/lib'
export type { SeriesFormat, SeriesResult } from '@/shared/lib'
export { fetchEventResults, fetchLiveSeries, fetchMySeries } from './api/seriesApi'
export type {
  EventResults, FmcAttemptState, LiveSeries, LiveSeriesMeetup, MySeries, ResultsRow, SavedAttempt, SeriesAttempt,
  SeriesStatus,
} from './model/types'
export { default as AttemptSeries } from './ui/AttemptSeries.vue'
export { default as ResultRow } from './ui/ResultRow.vue'

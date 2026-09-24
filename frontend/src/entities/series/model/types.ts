import type { Attempt, SeriesFormat } from '@/shared/lib'

export type SeriesStatus = 'in_progress' | 'completed'

/** Сохранённая попытка серии. */
export interface SavedAttempt extends Attempt {
  number: number
}

/** Своя серия участника (GET …/series/me, ответы на старт и сохранение попытки). */
export interface MySeries {
  id: number
  meetup_id: number
  event_id: string
  format: SeriesFormat
  status: SeriesStatus
  /** Версия для проверки одновременной записи, отправляется с попыткой. */
  version: number
  attempts: SavedAttempt[]
  best: number | null
  average: number | null
  /** Следующая попытка и её скрамбл; у завершённой серии null. */
  next_attempt: { number: number; scramble: string } | null
}

/** Строка таблицы дисциплины. */
export interface ResultsRow {
  /** null — без места: все попытки DNF или серия не закончена. */
  place: number | null
  user: { id: number; display_name: string }
  status: SeriesStatus
  /** По ячейке на каждую попытку формата, несобранные — null. */
  attempts: (Attempt | null)[]
  best: number | null
  average: number | null
  /** Отметки рекордов (entities не импортируют друг друга, поэтому без RecordMark). */
  marks: { single: ('PB' | 'LR')[]; average: ('PB' | 'LR')[] }
}

/** Таблица дисциплины на встрече. */
export interface EventResults {
  meetup: {
    id: number
    date: string
    status: 'planned' | 'live' | 'finished'
    club: { id: number; name: string; timezone: string }
  }
  event: { event_id: string; format: SeriesFormat }
  rows: ResultsRow[]
}

/** Своя серия на идущей встрече (GET /api/me/series). */
export interface LiveSeries {
  id: number
  event_id: string
  format: SeriesFormat
  status: SeriesStatus
  /** По ячейке на каждую попытку формата, несобранные — null. */
  attempts: (Attempt | null)[]
  best: number | null
  average: number | null
}

/** Идущая встреча и свои серии на ней. */
export interface LiveSeriesMeetup {
  id: number
  date: string
  club: { id: number; name: string; timezone: string }
  series: LiveSeries[]
}

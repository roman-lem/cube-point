import type { Attempt, SeriesFormat } from '@/shared/lib'

/** Попытка в таблице ввода; у FMC — с текстом решения. */
export interface DeskAttempt extends Attempt {
  solution?: string
  /** Попытку исправляли: в журнале больше одной записи. */
  edited?: boolean
  /** Исходный результат (первая запись журнала), только у исправленной. */
  original?: Attempt
}

/** Серия участника в таблице ввода организатора. */
export interface DeskSeries {
  id: number
  /** Версия для проверки одновременной записи. */
  version: number
  status: 'in_progress' | 'completed'
  /** По ячейке на каждую попытку формата, несобранные — null. */
  attempts: (DeskAttempt | null)[]
  best: number | null
  average: number | null
}

/** Строка таблицы ввода: подтверждённый участник и его серия (null — не начата). */
export interface DeskRow {
  user: { id: number; display_name: string }
  disqualified: boolean
  place: number | null
  marks: { single: ('PB' | 'LR')[]; average: ('PB' | 'LR')[] }
  series: DeskSeries | null
}

/** Дисциплина в панели организатора. Строки — по имени, а не по месту. */
export interface DeskEvent {
  event_id: string
  format: SeriesFormat
  rows: DeskRow[]
}

export interface DeskParticipant {
  user: { id: number; display_name: string; login: string }
  disqualification: { reason: string; created_at: string } | null
}

/** Панель встречи организатора (GET /api/meetups/:id/desk). */
export interface MeetupDesk {
  participants: DeskParticipant[]
  events: DeskEvent[]
}

/** Скрамблы дисциплины для печати бланков (без FMC). */
export interface PrintEvent {
  event_id: string
  format: SeriesFormat
  scrambles: string[]
}

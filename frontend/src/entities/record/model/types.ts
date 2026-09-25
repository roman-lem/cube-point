/** Отметка рекорда у результата: личный рекорд или рекорд клуба. */
export type RecordMark = 'PB' | 'LR'

export type RecordType = 'single' | 'average'

/** Встреча, на которой поставлен результат. Дата — уже в часовом поясе клуба. */
export interface RecordMeetup {
  id: number
  date: string
  club: { id: number; name: string }
}

/** Рекорд клуба (GET /api/clubs/<id>/records). */
export interface ClubRecord {
  value: number
  user: { id: number; display_name: string }
  meetup: RecordMeetup
  achieved_at: string
}

/** Рекорды клуба в дисциплине; null — рекорда нет (у bo-форматов нет среднего). */
export interface ClubEventRecords {
  event_id: string
  single: ClubRecord | null
  average: ClubRecord | null
}

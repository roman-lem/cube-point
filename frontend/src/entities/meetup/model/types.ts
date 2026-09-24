import type { SeriesFormat } from '@/shared/lib'

export type MeetupStatus = 'planned' | 'live' | 'finished'

export type RequestStatus = 'pending' | 'approved' | 'rejected'

/** Встреча в списке встреч клуба. Даты — ISO: date по часам клуба, *_at — UTC. */
export interface MeetupSummary {
  id: number
  date: string
  starts_at: string
  ends_at: string | null
  place: string | null
  address: string | null
  status: MeetupStatus
  events: string[]
  participants_count: number
}

export interface MeetupEvent {
  id: number
  event_id: string
  format: SeriesFormat
  /** Число начатых серий в дисциплине. */
  participants_count: number
  /** Лидер таблицы; только на странице встречи. */
  leader?: EventLeader | null
  /** Серия текущего пользователя; только на странице встречи. */
  my_series?: MyEventSeries | null
}

export interface EventLeader {
  display_name: string
  value: number
  /** Лидер показан средним (иначе — лучшей попыткой). */
  is_average: boolean
}

/** Серия текущего пользователя для карточки дисциплины. */
export interface MyEventSeries {
  status: 'in_progress' | 'completed'
  attempts_done: number
  best: number | null
  average: number | null
  /** null — без места: все попытки DNF или серия не закончена. */
  place: number | null
  /** Число строк в таблице дисциплины. */
  total: number
}

export interface Meetup extends Omit<MeetupSummary, 'events'> {
  club: { id: number; name: string; timezone: string }
  events: MeetupEvent[]
  /** Только для организатора и пока встреча не завершена. */
  join_token?: string
}

/** Страница встречи GET /api/meetups/:id. */
export interface MeetupPageData {
  meetup: Meetup
  /** Роль в клубе встречи (entities не импортируют друг друга, поэтому без ClubRole). */
  my_role: 'member' | 'organizer' | null
  my_request: { status: RequestStatus } | null
}

/** Встреча по ссылке-приглашению, для баннера на странице входа. */
export interface JoinPreview {
  id: number
  date: string
  starts_at: string
  place: string | null
  club: { id: number; name: string; timezone: string }
}

/** Идущая встреча, где пользователь подтверждён (GET /api/me/active). */
export interface ActiveMeetup {
  id: number
  date: string
  starts_at: string
  place: string | null
  club: { id: number; name: string }
  events: {
    event_id: string
    format: SeriesFormat
    /** Серия пользователя; null — не начата. */
    series: { status: 'in_progress' | 'completed'; attempts_done: number } | null
  }[]
}

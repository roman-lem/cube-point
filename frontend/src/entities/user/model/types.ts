import type { Attempt, EventId, SeriesFormat } from '@/shared/lib'

/** Вошедший пользователь, как его отдаёт /api/auth/me. */
export interface User {
  id: number
  login: string
  display_name: string
  email: string | null
  is_admin: boolean
  must_change_password: boolean
  /** Нет согласий текущей версии: пока их не дать, API недоступен. */
  consents_required: boolean
  /** Почему нельзя удалить аккаунт (последний организатор клуба) или null. */
  delete_restriction: string | null
}

/** Встреча, на которой поставлен личный рекорд. Дата — уже в часовом поясе клуба. */
export interface ProfileMeetupRef {
  id: number
  date: string
  club: { id: number; name: string }
}

/** Личный рекорд: null — удачных результатов нет (у bo-форматов нет среднего). */
export interface PersonalBest {
  value: number
  meetup: ProfileMeetupRef
}

/** Публичный профиль участника (GET /api/users/<id>). Логина в нём нет. */
export interface UserProfile {
  user: { id: number; display_name: string }
  /** Клубы, где человек состоит (без клубов, где он заблокирован). */
  clubs: { id: number; name: string }[]
  /** Встречи с результатами, кроме тех, где его дисквалифицировали. */
  meetups_count: number
  /** По дисциплинам, где у человека есть серии. */
  personal_records: {
    event_id: EventId
    single: PersonalBest | null
    average: PersonalBest | null
  }[]
}

/** Попытка в истории; у исправленной организатором — отметка и исходное значение. */
export interface ProfileAttempt extends Attempt {
  edited?: boolean
  original?: Attempt
}

/** Результат в дисциплине встречи. Отметки — только актуальные рекорды. */
export interface ProfileEventResult {
  event_id: EventId
  format: SeriesFormat
  status: 'in_progress' | 'completed'
  /** По ячейке на каждую попытку формата, несобранные — null. */
  attempts: (ProfileAttempt | null)[]
  best: number | null
  average: number | null
  marks: { single: ('PB' | 'LR')[]; average: ('PB' | 'LR')[] }
}

export interface ProfileMeetup extends ProfileMeetupRef {
  status: 'planned' | 'live' | 'finished'
  events: ProfileEventResult[]
}

/** Страница истории встреч (GET /api/users/<id>/meetups). */
export interface UserMeetupsPage {
  meetups: ProfileMeetup[]
  has_more: boolean
}

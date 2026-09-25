import type { EventId, SeriesFormat } from '@/shared/lib'

export type ClubRole = 'member' | 'organizer'

export type LinkType = 'vk' | 'youtube' | 'site' | 'other'

/** Цвета логотипа, как CLUB_COLORS в backend/app/models.py. */
export const LOGO_COLORS = ['blue', 'sky', 'teal', 'amber', 'orange', 'rose', 'slate', 'brown'] as const

export type LogoColor = (typeof LOGO_COLORS)[number]

export interface ClubLink {
  type: LinkType
  url: string
}

export interface Club {
  id: number
  name: string
  city: string
  timezone: string
  description: string | null
  logo_color: LogoColor
  links: ClubLink[]
}

/** Клуб в списке GET /api/clubs. */
export interface ClubSummary {
  id: number
  name: string
  city: string
  logo_color: LogoColor
  my_role: ClubRole | null
  live_meetup_id: number | null
}

/** Страница клуба GET /api/clubs/:id. */
export interface ClubPageData {
  club: Club
  my_role: ClubRole | null
  banned: boolean
}

/** Пользователь в администрировании: организатор или найденный по логину. */
export interface UserRef {
  id: number
  display_name: string
  login: string
}

/** Клуб в списке администратора GET /api/admin/clubs. */
export interface AdminClubSummary {
  id: number
  name: string
  city: string
  logo_color: LogoColor
  members_count: number
  organizers_count: number
  /** Дата последней проведённой встречи (YYYY-MM-DD) или null. */
  last_meetup_date: string | null
}

/** Клуб в администрировании GET /api/admin/clubs/:id. */
export interface AdminClub {
  id: number
  name: string
  city: string
  timezone: string
  logo_color: LogoColor
  members_count: number
  /** Проведённые встречи (идут или завершены). */
  meetups_count: number
  organizers: UserRef[]
}

/** Фильтр списка участников клуба (для организатора). */
export type MemberFilter = 'all' | 'organizers' | 'banned'

/** Участник в списке GET /api/clubs/:id/members. */
export interface ClubMemberSummary {
  /** Логин есть только в ответе организатору и администратору. */
  user: { id: number; display_name: string; login?: string }
  role: ClubRole
  banned: boolean
  /** Встречи клуба, где у человека есть хотя бы одна серия. */
  meetups_count: number
  /** Текущие рекорды клуба (LR) человека. */
  records_count: number
}

export interface ClubMembersList {
  members: ClubMemberSummary[]
  /** Организатор или администратор: видит заблокированных, фильтры и карточки. */
  can_manage: boolean
  /** Только для can_manage: сколько людей в каждом фильтре с учётом поиска. */
  filter_counts?: Record<MemberFilter, number>
}

/** Результат участника в дисциплине встречи. */
export interface MemberEventResult {
  event_id: EventId
  format: SeriesFormat
  status: 'in_progress' | 'completed'
  best: number | null
  average: number | null
  place: number | null
  /** Отметки рекордов (entities не импортируют друг друга, поэтому без RecordMark). */
  marks: { single: ('PB' | 'LR')[]; average: ('PB' | 'LR')[] }
}

export interface MemberMeetup {
  id: number
  date: string
  place: string | null
  status: 'planned' | 'live' | 'finished'
  disqualification: { reason: string; created_at: string } | null
  events: MemberEventResult[]
}

/** Действие в карточке участника: null — доступно, строка — почему недоступно. */
export type Restriction = string | null

/** Карточка участника GET /api/clubs/:id/members/:userId (организатору). */
export interface ClubMemberCard {
  user: UserRef
  role: ClubRole
  joined_at: string
  ban: {
    reason: string
    banned_at: string
    banned_by: { id: number; display_name: string } | null
  } | null
  meetups_count: number
  /** Встречи от новых к старым. */
  meetups: MemberMeetup[]
  /** Идущая встреча, где участник подтверждён: блокировка прервёт его серии. */
  live_meetup: { id: number; date: string } | null
  restrictions: {
    reset_password: Restriction
    organizer: Restriction
    ban: Restriction
  }
}

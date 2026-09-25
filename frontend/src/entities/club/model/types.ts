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

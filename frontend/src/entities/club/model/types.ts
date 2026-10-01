import type { EventId, SeriesFormat } from '@/shared/lib'

export type ClubRole = 'member' | 'organizer'

export type LinkType = 'vk' | 'youtube' | 'site' | 'other'

/** Logo colors, as CLUB_COLORS in backend/app/models.py. */
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

/** A club in the GET /api/clubs list (clubs with the most recent meetups first). */
export interface ClubSummary {
  id: number
  name: string
  city: string
  logo_color: LogoColor
  my_role: ClubRole | null
  live_meetup_id: number | null
  /** Members without banned ones. */
  member_count: number
  /** Started and finished meetups, without planned ones. */
  meetup_count: number
  /** Date of the latest such meetup ("2026-09-12", in the club's time zone), or null. */
  last_meetup_date: string | null
}

/** The organizer pledge text to accept (backend/app/pledge.py). */
export interface OrganizerPledge {
  version: string
  text: string
}

/** Club page GET /api/clubs/:id. */
export interface ClubPageData {
  club: Club
  my_role: ClubRole | null
  banned: boolean
  /** An organizer without the accepted pledge: their organizer tools are closed. Otherwise null. */
  pledge: OrganizerPledge | null
}

/** A user in administration: an organizer or one found by login. */
export interface UserRef {
  id: number
  display_name: string
  login: string
}

/** A club in the administrator's list GET /api/admin/clubs. */
export interface AdminClubSummary {
  id: number
  name: string
  city: string
  logo_color: LogoColor
  members_count: number
  organizers_count: number
  /** Date of the latest held meetup (YYYY-MM-DD), or null. */
  last_meetup_date: string | null
}

/** A club in administration GET /api/admin/clubs/:id. */
export interface AdminClub {
  id: number
  name: string
  city: string
  timezone: string
  logo_color: LogoColor
  members_count: number
  /** Held meetups (live or finished). */
  meetups_count: number
  organizers: UserRef[]
  /** What deleting the club takes with it: all meetups, all members, saved attempts. */
  deletion: { meetups: number; members: number; results: number }
  /** Why the club cannot be deleted now (a meetup is live), or null. */
  delete_restriction: Restriction
}

/** Club member list filter (for organizers). */
export type MemberFilter = 'all' | 'organizers' | 'banned'

/** A member in the GET /api/clubs/:id/members list. */
export interface ClubMemberSummary {
  /** The login is present only in the response to organizers and the administrator. */
  user: { id: number; display_name: string; login?: string }
  role: ClubRole
  banned: boolean
  /** Club meetups where the person has at least one series. */
  meetups_count: number
  /** The person's current club records (LR). */
  records_count: number
}

export interface ClubMembersList {
  members: ClubMemberSummary[]
  /** Organizer or administrator: sees banned members, filters and cards. */
  can_manage: boolean
  /** Only for can_manage: how many people are in each filter, with the search applied. */
  filter_counts?: Record<MemberFilter, number>
}

/** A member's result in a meetup event. */
export interface MemberEventResult {
  event_id: EventId
  format: SeriesFormat
  status: 'in_progress' | 'completed'
  best: number | null
  average: number | null
  place: number | null
  /** Record marks (entities do not import each other, hence no RecordMark). */
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

/** An action in the member card: null means available, a string says why not. */
export type Restriction = string | null

/** Member card GET /api/clubs/:id/members/:userId (for organizers). */
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
  /** Meetups, newest first. */
  meetups: MemberMeetup[]
  /** The live meetup where the member is approved: a ban interrupts their series. */
  live_meetup: { id: number; date: string } | null
  /** Display name changes, newest first: NameChange of entities/user
   * (entities do not import each other). */
  name_history: { old_name: string; new_name: string; changed_at: string; by_admin: boolean }[]
  restrictions: {
    reset_password: Restriction
    organizer: Restriction
    ban: Restriction
  }
}

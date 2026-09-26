import type { SeriesFormat } from '@/shared/lib'

export type MeetupStatus = 'planned' | 'live' | 'finished'

export type RequestStatus = 'pending' | 'approved' | 'rejected'

/** A meetup in the club's meetup list. Dates are ISO: date by the club's clock, *_at in UTC. */
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
  /** Number of started series in the event. */
  participants_count: number
  /** Table leader; only on the meetup page. */
  leader?: EventLeader | null
  /** Current user's series; only on the meetup page. */
  my_series?: MyEventSeries | null
}

export interface EventLeader {
  display_name: string
  value: number
  /** The leader is shown by the average (otherwise by the best attempt). */
  is_average: boolean
}

/** Current user's series for the event card. */
export interface MyEventSeries {
  status: 'in_progress' | 'completed'
  attempts_done: number
  best: number | null
  average: number | null
  /** null means no place: all attempts DNF or the series is unfinished. */
  place: number | null
  /** Number of rows in the event table. */
  total: number
}

export interface Meetup extends Omit<MeetupSummary, 'events'> {
  club: { id: number; name: string; timezone: string }
  events: MeetupEvent[]
  /** Only for organizers and only until the meetup is finished. */
  join_token?: string
}

/** Meetup page GET /api/meetups/:id. */
export interface MeetupPageData {
  meetup: Meetup
  /** Role in the meetup's club (entities do not import each other, hence no ClubRole). */
  my_role: 'member' | 'organizer' | null
  my_request: { status: RequestStatus } | null
}

/** A meetup from an invitation link, for the banner on the login page. */
export interface JoinPreview {
  id: number
  date: string
  starts_at: string
  place: string | null
  club: { id: number; name: string; timezone: string }
}

/** A live meetup where the user is approved (GET /api/me/active). */
export interface ActiveMeetup {
  id: number
  date: string
  starts_at: string
  place: string | null
  club: { id: number; name: string }
  events: {
    event_id: string
    format: SeriesFormat
    /** The user's series; null means not started. */
    series: { status: 'in_progress' | 'completed'; attempts_done: number } | null
  }[]
}

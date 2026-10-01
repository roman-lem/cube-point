import type { Attempt, EventId, SeriesFormat } from '@/shared/lib'

/** The user's email: confirmed, and the one waiting for confirmation by the link in a letter. */
export interface EmailState {
  /** Only a confirmed address. */
  email: string | null
  /** expired: the 24-hour link has expired, the letter has to be sent again. */
  pending_email: { address: string; expired: boolean } | null
}

/** The logged-in user as returned by /api/auth/me. */
export interface User extends EmailState {
  id: number
  login: string
  display_name: string
  is_admin: boolean
  must_change_password: boolean
  /** No current-version consents: the API is unavailable until they are given. */
  consents_required: boolean
  /** Why the account cannot be deleted (last organizer of a club), or null. */
  delete_restriction: string | null
  /** When the display name can be changed again (once in 30 days), null if now. */
  display_name_change_available_at: string | null
}

/** A display name change. by_admin: the previous name was returned by an administrator. */
export interface NameChange {
  old_name: string
  new_name: string
  changed_at: string
  by_admin: boolean
}

/** The meetup where a personal best was set. The date is already in the club's time zone. */
export interface ProfileMeetupRef {
  id: number
  date: string
  club: { id: number; name: string }
}

/** Personal best: null means no successful results (bo formats have no average). */
export interface PersonalBest {
  value: number
  meetup: ProfileMeetupRef
}

/** A member's public profile (GET /api/users/<id>). It has no login. */
export interface UserProfile {
  user: { id: number; display_name: string }
  /** Clubs the person is a member of (without clubs where they are banned). */
  clubs: { id: number; name: string }[]
  /** Meetups with results, except those where they were disqualified. */
  meetups_count: number
  /** Per event where the person has series. */
  personal_records: {
    event_id: EventId
    single: PersonalBest | null
    average: PersonalBest | null
  }[]
}

/** An attempt in the history; one corrected by an organizer has a mark and the original value. */
export interface ProfileAttempt extends Attempt {
  edited?: boolean
  original?: Attempt
  /** FMC solution: of a finished meetup, or the person's own. */
  solution?: string
}

/** A result in a meetup event. Marks are current records only. */
export interface ProfileEventResult {
  event_id: EventId
  format: SeriesFormat
  status: 'in_progress' | 'completed'
  /** A cell for each attempt of the format, null for attempts not yet done. */
  attempts: (ProfileAttempt | null)[]
  best: number | null
  average: number | null
  marks: { single: ('PB' | 'LR')[]; average: ('PB' | 'LR')[] }
}

export interface ProfileMeetup extends ProfileMeetupRef {
  status: 'planned' | 'live' | 'finished'
  events: ProfileEventResult[]
}

/** A page of meetup history (GET /api/users/<id>/meetups). */
export interface UserMeetupsPage {
  meetups: ProfileMeetup[]
  has_more: boolean
}

import type { Attempt, SeriesFormat } from '@/shared/lib'

export type SeriesStatus = 'in_progress' | 'completed'

/** An attempt in tables and series. One corrected by an organizer has a mark and the original value. */
export interface SeriesAttempt extends Attempt {
  edited?: boolean
  original?: Attempt
  /**
   * FMC solution. Other participants' solutions come only after the meetup is finished,
   * the person's own always.
   */
  solution?: string
}

/** A saved attempt of a series. */
export interface SavedAttempt extends SeriesAttempt {
  number: number
}

/** A started FMC attempt (timestamps are ISO in UTC). */
export interface FmcAttemptState {
  started_at: string
  deadline: string
  /** Server time at the moment of the response: the client corrects its clock by it. */
  server_now: string
  /** The last solution draft saved on the server. */
  draft: string
  /** The solution frozen at submission; null means not frozen. */
  frozen_solution: string | null
  frozen_at: string | null
}

/** A participant's own series (GET …/series/me, responses to start and attempt save). */
export interface MySeries {
  id: number
  meetup_id: number
  event_id: string
  format: SeriesFormat
  status: SeriesStatus
  /** Version for the concurrent edit check, sent with the attempt. */
  version: number
  attempts: SavedAttempt[]
  best: number | null
  average: number | null
  /** The next attempt and its scramble; null for a finished series. */
  next_attempt: {
    number: number
    /** In FMC the scramble exists only after the attempt starts. */
    scramble: string | null
    /** FMC only: attempt state, null means not started yet. */
    fmc?: FmcAttemptState | null
  } | null
}

/** Event table row. */
export interface ResultsRow {
  /** null means no place: all attempts DNF or the series is unfinished. */
  place: number | null
  /** has_profile is false for a deleted account that kept its name: the name has no link. */
  user: { id: number; display_name: string; has_profile: boolean }
  status: SeriesStatus
  /** A cell for each attempt of the format, null for attempts not yet done. */
  attempts: (SeriesAttempt | null)[]
  best: number | null
  average: number | null
  /** Record marks (entities do not import each other, hence no RecordMark). */
  marks: { single: ('PB' | 'LR')[]; average: ('PB' | 'LR')[] }
}

/** Event table at a meetup. */
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

/** One's own series at a live meetup (GET /api/me/series). */
export interface LiveSeries {
  id: number
  event_id: string
  format: SeriesFormat
  status: SeriesStatus
  /** A cell for each attempt of the format, null for attempts not yet done. */
  attempts: (SeriesAttempt | null)[]
  best: number | null
  average: number | null
}

/** A live meetup and one's own series at it. */
export interface LiveSeriesMeetup {
  id: number
  date: string
  club: { id: number; name: string; timezone: string }
  series: LiveSeries[]
}

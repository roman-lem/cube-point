import type { Attempt, SeriesFormat } from '@/shared/lib'

/** An attempt in the entry table; FMC ones include the solution text. */
export interface DeskAttempt extends Attempt {
  solution?: string
  /** The attempt was corrected: more than one history entry. */
  edited?: boolean
  /** Original result (the first history entry), only for a corrected attempt. */
  original?: Attempt
}

/** A participant's series in the organizer's entry table. */
export interface DeskSeries {
  id: number
  /** Version for the concurrent edit check. */
  version: number
  status: 'in_progress' | 'completed'
  /** A cell for each attempt of the format, null for attempts not yet done. */
  attempts: (DeskAttempt | null)[]
  best: number | null
  average: number | null
}

/** Entry table row: an approved participant and their series (null: not started). */
export interface DeskRow {
  user: { id: number; display_name: string }
  disqualified: boolean
  place: number | null
  marks: { single: ('PB' | 'LR')[]; average: ('PB' | 'LR')[] }
  series: DeskSeries | null
}

/** An event in the organizer desk. Rows are sorted by name, not by place. */
export interface DeskEvent {
  event_id: string
  format: SeriesFormat
  rows: DeskRow[]
}

export interface DeskParticipant {
  /** login is null if the participant deleted their account. */
  user: { id: number; display_name: string; login: string | null }
  disqualification: { reason: string; created_at: string } | null
}

/** Organizer's meetup desk (GET /api/meetups/:id/desk). */
export interface MeetupDesk {
  participants: DeskParticipant[]
  events: DeskEvent[]
}

/** Event scrambles for printing score sheets (without FMC). */
export interface PrintEvent {
  event_id: string
  format: SeriesFormat
  scrambles: string[]
}

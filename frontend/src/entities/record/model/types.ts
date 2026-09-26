/** Record mark on a result: personal best or club record. */
export type RecordMark = 'PB' | 'LR'

export type RecordType = 'single' | 'average'

/** The meetup where the result was set. The date is already in the club's time zone. */
export interface RecordMeetup {
  id: number
  date: string
  club: { id: number; name: string }
}

/** Club record (GET /api/clubs/<id>/records). */
export interface ClubRecord {
  value: number
  /** has_profile is false for a deleted account that kept its name: the name has no link. */
  user: { id: number; display_name: string; has_profile: boolean }
  meetup: RecordMeetup
  achieved_at: string
}

/** Club records in an event; null means no record (bo formats have no average). */
export interface ClubEventRecords {
  event_id: string
  single: ClubRecord | null
  average: ClubRecord | null
}

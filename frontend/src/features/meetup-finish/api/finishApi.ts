import type { Meetup } from '@/entities/meetup'
import { http } from '@/shared/api'
import type { Attempt } from '@/shared/lib'

/** A started but unsubmitted FMC attempt: the organizer resolves it before finishing. */
export interface UnresolvedFmc {
  series_id: number
  version: number
  attempt_number: number
  user: { id: number; display_name: string; login: string | null }
  scramble: string
  /** The frozen solution or (if there was no submission) the last draft. */
  solution: string
  /** frozen: submission not confirmed, expired: the hour ran out, running: the hour is on. */
  state: 'frozen' | 'expired' | 'running'
  deadline: string
}

export interface FinishSummary {
  /** Participants with unfinished series. */
  unfinished: {
    user: { id: number; display_name: string; login: string | null }
    events: { event_id: string; attempts_done: number; attempts_count: number }[]
  }[]
  /** How many attempts will become DNS. */
  dns_count: number
  fmc: UnresolvedFmc[]
}

const base = (meetupId: number) => `/api/meetups/${meetupId}`

export function fetchFinishSummary(meetupId: number) {
  return http.get<FinishSummary>(`${base(meetupId)}/finish-summary`)
}

/** Result of an FMC attempt checked in the organizer's browser, or DNF. */
export function resolveFmc(meetupId: number, item: UnresolvedFmc, result: Attempt) {
  return http.post<void>(
    `${base(meetupId)}/fmc/${item.series_id}/${item.attempt_number}/resolve`,
    { ...result, version: item.version, solution: item.solution },
  )
}

export async function finishMeetup(meetupId: number) {
  return (await http.post<{ meetup: Meetup }>(`${base(meetupId)}/finish`)).meetup
}

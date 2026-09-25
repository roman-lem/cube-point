import type { Meetup } from '@/entities/meetup'
import { http } from '@/shared/api'
import type { Attempt } from '@/shared/lib'

/** Начатая, но не сданная попытка FMC: её организатор разрешает до завершения. */
export interface UnresolvedFmc {
  series_id: number
  version: number
  attempt_number: number
  user: { id: number; display_name: string; login: string | null }
  scramble: string
  /** Замороженное решение или (если сдачи не было) последний черновик. */
  solution: string
  /** frozen — сдача не подтверждена, expired — час вышел, running — час идёт. */
  state: 'frozen' | 'expired' | 'running'
  deadline: string
}

export interface FinishSummary {
  /** Участники с незавершёнными сериями. */
  unfinished: {
    user: { id: number; display_name: string; login: string | null }
    events: { event_id: string; attempts_done: number; attempts_count: number }[]
  }[]
  /** Сколько попыток станут DNS. */
  dns_count: number
  fmc: UnresolvedFmc[]
}

const base = (meetupId: number) => `/api/meetups/${meetupId}`

export function fetchFinishSummary(meetupId: number) {
  return http.get<FinishSummary>(`${base(meetupId)}/finish-summary`)
}

/** Результат попытки FMC, проверенной в браузере организатора, или DNF. */
export function resolveFmc(meetupId: number, item: UnresolvedFmc, result: Attempt) {
  return http.post<void>(
    `${base(meetupId)}/fmc/${item.series_id}/${item.attempt_number}/resolve`,
    { ...result, version: item.version, solution: item.solution },
  )
}

export async function finishMeetup(meetupId: number) {
  return (await http.post<{ meetup: Meetup }>(`${base(meetupId)}/finish`)).meetup
}

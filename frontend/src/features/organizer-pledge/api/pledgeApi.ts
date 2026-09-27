import { http } from '@/shared/api'

/** Accepts the organizer pledge in the club: the version of the text that was displayed. */
export function acceptPledge(clubId: number, version: string) {
  return http.post<void>(`/api/clubs/${clubId}/organizer-pledge`, { version })
}

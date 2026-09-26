import { http } from '@/shared/api'
import type { UserMeetupsPage, UserProfile } from '../model/types'

/** A member's public profile: clubs, number of meetups, personal bests. */
export function fetchUserProfile(userId: number) {
  return http.get<UserProfile>(`/api/users/${userId}`)
}

/** A member's meetup history, newest first; offset is how many meetups are already loaded. */
export function fetchUserMeetups(userId: number, offset = 0) {
  return http.get<UserMeetupsPage>(`/api/users/${userId}/meetups?offset=${offset}`)
}

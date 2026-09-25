import { http } from '@/shared/api'
import type { UserMeetupsPage, UserProfile } from '../model/types'

/** Публичный профиль участника: клубы, число встреч, личные рекорды. */
export function fetchUserProfile(userId: number) {
  return http.get<UserProfile>(`/api/users/${userId}`)
}

/** История встреч участника, от новых к старым; offset — сколько встреч уже загружено. */
export function fetchUserMeetups(userId: number, offset = 0) {
  return http.get<UserMeetupsPage>(`/api/users/${userId}/meetups?offset=${offset}`)
}

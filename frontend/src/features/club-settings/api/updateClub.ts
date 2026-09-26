import type { Club, ClubLink, LogoColor } from '@/entities/club'
import { http } from '@/shared/api'

export interface ClubSettings {
  name: string
  city: string
  description: string
  logo_color: LogoColor
  /** Replace all club links, the order is kept. */
  links: ClubLink[]
}

export async function updateClub(clubId: number, data: ClubSettings) {
  return (await http.patch<{ club: Club }>(`/api/clubs/${clubId}`, data)).club
}

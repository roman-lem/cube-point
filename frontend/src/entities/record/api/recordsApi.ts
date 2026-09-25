import { http } from '@/shared/api'
import type { ClubEventRecords } from '../model/types'

/** Рекорды клуба по дисциплинам (сингл и среднее). */
export async function fetchClubRecords(clubId: number) {
  return (await http.get<{ records: ClubEventRecords[] }>(`/api/clubs/${clubId}/records`)).records
}

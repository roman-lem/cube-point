import { http } from '@/shared/api'
import type { ClubEventRecords } from '../model/types'

/** Club records per event (single and average). */
export async function fetchClubRecords(clubId: number) {
  return (await http.get<{ records: ClubEventRecords[] }>(`/api/clubs/${clubId}/records`)).records
}

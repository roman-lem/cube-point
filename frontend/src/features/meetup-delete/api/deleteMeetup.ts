import { http } from '@/shared/api'

// Administrator only, see backend/app/admin.py.

/** What deleting the meetup takes with it and why it cannot be deleted now (or null). */
export interface MeetupDeletion {
  deletion: {
    /** All requests, pending and rejected too. */
    requests: number
    /** People with at least one series. */
    participants: number
    /** Saved attempts. */
    results: number
  }
  delete_restriction: string | null
}

export async function fetchMeetupDeletion(meetupId: number) {
  return http.get<MeetupDeletion>(`/api/admin/meetups/${meetupId}/deletion`)
}

/** Deletes the meetup with everything in it; club records are recalculated. */
export async function deleteMeetup(meetupId: number) {
  await http.delete<void>(`/api/admin/meetups/${meetupId}`)
}

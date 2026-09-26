import { useStorage, type StorageLike } from '@vueuse/core'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import {
  addSolve,
  parseSession,
  removeSolve,
  serializeSession,
  sessionStats,
  setPenalty,
  type TrainingPenalty,
  type TrainingSolve,
} from './session'

export const sessionKey = (eventId: string) => `training-session:${eventId}`

/**
 * Training session of an event in localStorage. Survives a reload and
 * is not sent to the server. Instances on one page (timer,
 * statistics) see the same data. When eventId changes, the session
 * of the other event is read.
 *
 * storage is for tests; if storage is unavailable (private mode),
 * the session lives only in memory.
 */
export function useTrainingSession(eventId: MaybeRefOrGetter<string>, storage?: StorageLike) {
  // The session is changed only by replacing the array: useStorage returns
  // the default empty array as the same object.
  const solves = useStorage<TrainingSolve[]>(() => sessionKey(toValue(eventId)), [], storage, {
    serializer: { read: parseSession, write: serializeSession },
    writeDefaults: false,
    // Synchronous writes: with the deferred ('pre') flush, a write queued
    // before an event change went under the new event's key.
    flush: 'sync',
  })

  return {
    solves: computed(() => solves.value),
    stats: computed(() => sessionStats(solves.value)),
    last: computed(() => solves.value[solves.value.length - 1] ?? null),
    add(value: number, penalty: TrainingPenalty) {
      solves.value = addSolve(solves.value, value, penalty)
    },
    setPenalty(at: number, penalty: TrainingPenalty) {
      solves.value = setPenalty(solves.value, at, penalty)
    },
    remove(at: number) {
      solves.value = removeSolve(solves.value, at)
    },
    clear() {
      solves.value = []
    },
  }
}

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
 * Тренировочная сессия дисциплины в localStorage. Переживает перезагрузку,
 * на сервер не отправляется. Экземпляры на одной странице (таймер,
 * статистика) видят одни и те же данные. При смене eventId читается
 * сессия другой дисциплины.
 *
 * storage — для тестов; если хранилище недоступно (приватный режим),
 * сессия живёт только в памяти.
 */
export function useTrainingSession(eventId: MaybeRefOrGetter<string>, storage?: StorageLike) {
  // Сессию меняем только заменой массива: пустой массив по умолчанию
  // useStorage отдаёт одним и тем же объектом.
  const solves = useStorage<TrainingSolve[]>(() => sessionKey(toValue(eventId)), [], storage, {
    serializer: { read: parseSession, write: serializeSession },
    writeDefaults: false,
    // Синхронная запись: с отложенной ('pre') запись, поставленная в очередь
    // до смены дисциплины, уходила уже под ключ новой дисциплины.
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

import { ref, shallowReactive } from 'vue'
import type { DeskEvent } from '@/entities/meetup'
import { ApiError } from '@/shared/api'
import { eventName, type Attempt } from '@/shared/lib'
import { deleteAttempt, restoreAttempt, saveAttempt } from '../api/saveAttempt'

/** Save state of a cell. No state means nothing is happening. */
export interface CellState {
  status: 'saving' | 'saved' | 'error'
  message?: string
  /** Retry saving the same value. */
  retry?: () => void
}

const SAVED_VISIBLE_MS = 2000

export const INVALID_INPUT_MESSAGE = 'Не понимаю ввод: время 1234 или 12.34, «+» — +2, «d» — DNF'

function cellKey(eventId: string, userId: number, number: number) {
  return `${eventId}:${userId}:${number}`
}

/**
 * Autosave for manual entry: each cell has its own state.
 *
 * attempt = null erases the attempt (only the last one in the series and not one submitted
 * by the participant; the server checks). restore returns the attempt to its original result.
 *
 * Saves of one series go in order and take the series version at the moment
 * of sending: otherwise quickly entering two attempts in a row would cause a false conflict.
 */
export function useAttemptSaving(options: {
  meetupId: () => number
  /** Current version of the participant's series; null means no series yet. */
  version: (eventId: string, userId: number) => number | null
  /** Fresh event data: after a save and on a conflict. */
  onEvent: (event: DeskEvent) => void
}) {
  const states = shallowReactive(new Map<string, CellState>())
  /** Version conflict message above the table. */
  const notice = ref('')
  const queues = new Map<string, Promise<void>>()
  const timers = new Map<string, ReturnType<typeof setTimeout>>()

  function setState(key: string, state: CellState | null) {
    clearTimeout(timers.get(key))
    if (state) {
      states.set(key, state)
    } else {
      states.delete(key)
    }
  }

  /** A cell request in the series queue. send gets the series version at the moment of sending. */
  function enqueue(
    eventId: string,
    user: { id: number; display_name: string },
    number: number,
    send: (version: number | null) => Promise<DeskEvent>,
  ): Promise<void> {
    const key = cellKey(eventId, user.id, number)
    const retry = () => void enqueue(eventId, user, number, send)
    setState(key, { status: 'saving' })

    const run = async () => {
      try {
        const event = await send(options.version(eventId, user.id))
        options.onEvent(event)
        setState(key, { status: 'saved' })
        timers.set(key, setTimeout(() => states.delete(key), SAVED_VISIBLE_MS))
      } catch (e) {
        if (e instanceof ApiError && e.data.event) {
          options.onEvent(e.data.event as DeskEvent)
        }
        if (e instanceof ApiError && e.code === 'version_conflict') {
          notice.value =
            `${user.display_name}, ${eventName(eventId)}: серию только что изменили ` +
            '(участник или другой организатор). Строка обновлена — проверьте попытку ' +
            'и при необходимости введите её заново.'
          setState(key, { status: 'error', message: 'Серию изменили, данные обновлены', retry })
        } else {
          const message = e instanceof ApiError ? e.message : 'Не удалось сохранить'
          // Retrying makes sense on a network or server failure, not on a rule rejection.
          const retryable = !(e instanceof ApiError) || e.status === 0 || e.status >= 500
          setState(key, { status: 'error', message, retry: retryable ? retry : undefined })
        }
      }
    }

    const rowKey = `${eventId}:${user.id}`
    const next = (queues.get(rowKey) ?? Promise.resolve()).then(run)
    queues.set(rowKey, next)
    return next
  }

  function save(
    eventId: string,
    user: { id: number; display_name: string },
    number: number,
    attempt: Attempt | null,
  ): Promise<void> {
    return enqueue(eventId, user, number, (version) =>
      attempt
        ? saveAttempt(options.meetupId(), eventId, user.id, number, attempt, version)
        : deleteAttempt(options.meetupId(), eventId, user.id, number, version),
    )
  }

  function restore(
    eventId: string,
    user: { id: number; display_name: string },
    number: number,
  ): Promise<void> {
    return enqueue(eventId, user, number, (version) =>
      restoreAttempt(options.meetupId(), eventId, user.id, number, version),
    )
  }

  function stateOf(eventId: string, userId: number, number: number) {
    return states.get(cellKey(eventId, userId, number))
  }

  /** Input error before sending to the server (e.g. "12..3"). */
  function markInvalid(eventId: string, userId: number, number: number) {
    setState(cellKey(eventId, userId, number), { status: 'error', message: INVALID_INPUT_MESSAGE })
  }

  return { notice, meetupId: options.meetupId, save, restore, stateOf, markInvalid }
}

export type AttemptSaving = ReturnType<typeof useAttemptSaving>

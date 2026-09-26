// Events and formats. Mirror of backend/app/events.py: the IDs
// and default formats must match, the names are for the UI only.
import type { ResultType, SeriesFormat } from './results'

export type EventId = '333' | '222' | '333oh' | 'pyram' | '333fm' | '333bf'

export interface EventInfo {
  /** Short name for cards and lists: 3x3, OH, FMC. */
  name: string
  /** Name with an explanation for choosing the event when creating a meetup. */
  fullName: string
  resultType: ResultType
  defaultFormat: SeriesFormat
}

export const EVENTS: Record<EventId, EventInfo> = {
  '333': { name: '3x3', fullName: '3x3', resultType: 'time', defaultFormat: 'ao5' },
  '222': { name: '2x2', fullName: '2x2', resultType: 'time', defaultFormat: 'ao5' },
  '333oh': { name: 'OH', fullName: 'OH (одной рукой)', resultType: 'time', defaultFormat: 'ao5' },
  pyram: { name: 'Пирамидка', fullName: 'Пирамидка', resultType: 'time', defaultFormat: 'ao5' },
  '333fm': { name: 'FMC', fullName: 'FMC', resultType: 'moves', defaultFormat: 'bo1' },
  '333bf': { name: '3BLD', fullName: '3BLD (вслепую)', resultType: 'time', defaultFormat: 'bo5' },
}

/**
 * Display order. A separate list: an object always iterates numeric keys ('222', '333')
 * first in ascending order, so the key order of EVENTS would not be kept.
 */
export const EVENT_IDS: EventId[] = ['333', '222', '333oh', 'pyram', '333fm', '333bf']

/** Events for the timer and training sessions: timed only, FMC has a separate screen. */
export const TIMER_EVENT_IDS = EVENT_IDS.filter((id) => EVENTS[id].resultType === 'time')

export const FORMAT_NAMES: Record<SeriesFormat, string> = {
  ao5: 'Среднее из 5',
  mo3: 'Среднее из 3',
  bo3: 'Лучшая из 3',
  bo5: 'Лучшая из 5',
  bo1: 'Одна попытка',
}

export const FORMATS = Object.keys(FORMAT_NAMES) as SeriesFormat[]

/** Event name; an unknown ID is shown as is. */
export function eventName(eventId: string): string {
  return EVENTS[eventId as EventId]?.name ?? eventId
}

/** Format label, e.g. «Среднее из 5 (ao5)». */
export function formatName(format: SeriesFormat): string {
  return `${FORMAT_NAMES[format]} (${format})`
}

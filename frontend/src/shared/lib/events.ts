// Дисциплины и форматы. Зеркало backend/app/events.py: идентификаторы
// и форматы по умолчанию должны совпадать, названия — только для интерфейса.
import type { ResultType, SeriesFormat } from './results'

export type EventId = '333' | '222' | '333oh' | 'pyram' | '333fm' | '333bf'

export interface EventInfo {
  /** Короткое название для карточек и списков: 3x3, OH, FMC. */
  name: string
  /** Название с пояснением для выбора дисциплины при создании встречи. */
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
 * Порядок показа. Отдельным списком: ключи-числа ('222', '333') объект
 * всегда перебирает первыми по возрастанию, порядок ключей EVENTS не сохранится.
 */
export const EVENT_IDS: EventId[] = ['333', '222', '333oh', 'pyram', '333fm', '333bf']

/** Дисциплины таймера и тренировочных сессий: только на время, FMC — отдельный экран. */
export const TIMER_EVENT_IDS = EVENT_IDS.filter((id) => EVENTS[id].resultType === 'time')

export const FORMAT_NAMES: Record<SeriesFormat, string> = {
  ao5: 'Среднее из 5',
  mo3: 'Среднее из 3',
  bo3: 'Лучшая из 3',
  bo5: 'Лучшая из 5',
  bo1: 'Одна попытка',
}

export const FORMATS = Object.keys(FORMAT_NAMES) as SeriesFormat[]

/** Название дисциплины; неизвестный идентификатор показывается как есть. */
export function eventName(eventId: string): string {
  return EVENTS[eventId as EventId]?.name ?? eventId
}

/** «Среднее из 5 (ao5)» */
export function formatName(format: SeriesFormat): string {
  return `${FORMAT_NAMES[format]} (${format})`
}

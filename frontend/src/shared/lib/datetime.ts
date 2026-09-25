// Даты и время встреч. Сервер отдаёт метки времени в UTC (ISO с «Z»),
// показываем их в часовом поясе клуба. Дата встречи ("2026-10-19")
// уже в часовом поясе клуба и пересчёта не требует.

const MONTHS = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]

/** "2026-10-19" → «19 октября»; год добавляется, если он не текущий. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  const text = `${day} ${MONTHS[month - 1]}`
  return year === new Date().getFullYear() ? text : `${text} ${year}`
}

/** Время "HH:MM" по часам клуба. */
export function formatTime(isoMoment: string, timeZone: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(isoMoment))
}

/** «18:00–21:00» или «18:00», если время окончания не указано. */
export function formatTimeRange(startsAt: string, endsAt: string | null, timeZone: string): string {
  const start = formatTime(startsAt, timeZone)
  return endsAt ? `${start}–${formatTime(endsAt, timeZone)}` : start
}

/** Сегодняшняя дата по часам клуба: "2026-10-19". */
export function todayIn(timeZone: string): string {
  // Шведская локаль даёт как раз формат YYYY-MM-DD.
  return new Intl.DateTimeFormat('sv-SE', { timeZone }).format(new Date())
}

/** Часовой пояс нового клуба по умолчанию — время Тюмени. */
export const DEFAULT_TIME_ZONE = 'Asia/Yekaterinburg'

/**
 * Часовые пояса IANA для выбора: «Asia/Yekaterinburg (GMT+5)».
 * Список — из браузера, сервер проверяет пояс по своей базе tzdata.
 */
export function timeZoneOptions(): { value: string; label: string }[] {
  const zones = Intl.supportedValuesOf('timeZone')
  if (!zones.includes(DEFAULT_TIME_ZONE)) {
    zones.push(DEFAULT_TIME_ZONE)
  }
  const now = new Date()
  return zones.sort().map((zone) => {
    const offset = new Intl.DateTimeFormat('en-US', { timeZone: zone, timeZoneName: 'shortOffset' })
      .formatToParts(now)
      .find((part) => part.type === 'timeZoneName')?.value
    return { value: zone, label: offset ? `${zone} (${offset})` : zone }
  })
}

// Meetup dates and times. The server returns timestamps in UTC (ISO with "Z"),
// they are shown in the club's time zone. The meetup date ("2026-10-19")
// is already in the club's time zone and needs no conversion.

const MONTHS = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]

/** "2026-10-19" → «19 октября»; the year is added if it is not the current one. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  const text = `${day} ${MONTHS[month - 1]}`
  return year === new Date().getFullYear() ? text : `${text} ${year}`
}

/** Time "HH:MM" by the club's clock. */
export function formatTime(isoMoment: string, timeZone: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(isoMoment))
}

/** «19 октября, 18:05» by the club's clock. */
export function formatDateTime(isoMoment: string, timeZone: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(isoMoment))
}

/** "18:00–21:00", or "18:00" if the end time is not set. */
export function formatTimeRange(startsAt: string, endsAt: string | null, timeZone: string): string {
  const start = formatTime(startsAt, timeZone)
  return endsAt ? `${start}–${formatTime(endsAt, timeZone)}` : start
}

/** Today's date by the club's clock: "2026-10-19". */
export function todayIn(timeZone: string): string {
  // The Swedish locale gives exactly the YYYY-MM-DD format.
  return new Intl.DateTimeFormat('sv-SE', { timeZone }).format(new Date())
}

/** Default time zone of a new club: Tyumen time. */
export const DEFAULT_TIME_ZONE = 'Asia/Yekaterinburg'

/**
 * IANA time zones to choose from: "Asia/Yekaterinburg (GMT+5)".
 * The list comes from the browser; the server validates the zone against its tzdata.
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

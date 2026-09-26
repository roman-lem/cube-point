import { describe, expect, it } from 'vitest'
import { formatDate, formatTime, formatTimeRange } from './datetime'

describe('datetime', () => {
  it('shows time by the club clock', () => {
    // Tyumen is UTC+5.
    expect(formatTime('2026-10-19T13:00:00Z', 'Asia/Yekaterinburg')).toBe('18:00')
    expect(formatTimeRange('2026-10-19T13:00:00Z', '2026-10-19T16:30:00Z', 'Asia/Yekaterinburg'))
      .toBe('18:00–21:30')
    expect(formatTimeRange('2026-10-19T13:00:00Z', null, 'Asia/Yekaterinburg')).toBe('18:00')
  })

  it('writes the date in words, with the year if it is not the current one', () => {
    const year = new Date().getFullYear()
    expect(formatDate(`${year}-10-01`)).toBe('1 октября')
    expect(formatDate('2020-03-15')).toBe('15 марта 2020')
  })
})

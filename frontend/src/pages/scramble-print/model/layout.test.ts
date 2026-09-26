import { describe, expect, it } from 'vitest'
import type { PrintEvent } from '@/entities/meetup'
import { layoutBlank } from './layout'

const SCRAMBLE_333 = "D2 F2 U' L2 D' R2 U' F2 U2 R2 B' L' U2 R D' B U' R' F R2"
const SCRAMBLE_777 = Array.from({ length: 100 }, (_, i) => (i % 2 ? '3Rw2' : 'Fw')).join(' ')
const MINX = Array.from({ length: 7 }, () => 'R-- D-- R++ D++ R-- D++ R-- D-- R++ D++ U').join(' ')

function event(eventId: string, scramble: string, count: number): PrintEvent {
  return { event_id: eventId, format: count === 5 ? 'ao5' : 'mo3', scrambles: Array(count).fill(scramble) }
}

describe('layoutBlank', () => {
  it('a small meetup fits one page with high rows', () => {
    const pages = layoutBlank([event('333', SCRAMBLE_333, 5), event('222', 'R U2 F', 5)])
    expect(pages).toHaveLength(1)
    expect(pages[0]!.rowHeight).toBe(8)
  })

  it('five ao5 events still fit one page with low rows', () => {
    const pages = layoutBlank(['333', '222', '333oh', 'pyram', '333bf'].map((id) => event(id, SCRAMBLE_333, 5)))
    expect(pages).toHaveLength(1)
    expect(pages[0]!.rowHeight).toBe(5.6)
  })

  it('long scrambles go to the next page, events keep their order and are not split', () => {
    const events = [
      event('333', SCRAMBLE_333, 5),
      event('666', SCRAMBLE_777, 3),
      event('777', SCRAMBLE_777, 3),
      event('minx', MINX, 5),
      event('sq1', '(-2, 0) / (0, -3) / (-4, 2)', 5),
    ]
    const pages = layoutBlank(events)
    expect(pages.length).toBeGreaterThan(1)
    expect(pages.flatMap((p) => p.events)).toEqual(events)
  })

  it('no events, no pages', () => {
    expect(layoutBlank([])).toEqual([])
  })
})

import type { PrintEvent } from '@/entities/meetup'
import { scrambleLines, scramblePieces } from '@/shared/lib'

// Splitting a score sheet into A5 pages. All the page's scrambles must fit on it,
// the heights are estimated from the fixed sheet layout in ScrambleBlank (in mm).
// An event is not split between pages.

export interface BlankPage {
  events: PrintEvent[]
  /** Minimum row height, mm: the fewer rows on the page, the more room to write the time. */
  rowHeight: number
}

/** Scrambles longer than this are printed in the small font. */
export const LONG_SCRAMBLE = 200

const ROW_HEIGHTS = [8, 6.8, 5.6]
// A5 without the padding (210 − 2 × 8), the header and a margin for estimate errors.
const PAGE_HEIGHT = 178
const EVENT_TITLE = 4.8 // title line and its margin
const EVENT_GAP = 2.5
const ROW_PADDING = 1.6
// Scramble column width ≈ 102 mm; JetBrains Mono is 0.6 em wide.
const NORMAL = { chars: 64, lineHeight: 3.18 } // 7.5pt
const SMALL = { chars: 74, lineHeight: 2.75 } // 6.5pt

export function layoutBlank(events: PrintEvent[]): BlankPage[] {
  const pages: PrintEvent[][] = []
  let current: PrintEvent[] = []
  for (const event of events) {
    if (current.length === 0 || fits([...current, event])) {
      current.push(event)
    } else {
      pages.push(current)
      current = [event]
    }
  }
  if (current.length > 0) {
    pages.push(current)
  }
  return pages.map((page) => ({
    events: page,
    // An event taller than a page gets a page of its own with the lowest rows.
    rowHeight: ROW_HEIGHTS.find((height) => pageHeight(page, height) <= PAGE_HEIGHT) ?? 5.6,
  }))
}

function fits(events: PrintEvent[]): boolean {
  return pageHeight(events, ROW_HEIGHTS[ROW_HEIGHTS.length - 1]!) <= PAGE_HEIGHT
}

function pageHeight(events: PrintEvent[], rowHeight: number): number {
  let height = 0
  for (const event of events) {
    height += EVENT_GAP + EVENT_TITLE
    for (const scramble of event.scrambles) {
      height += Math.max(rowHeight, scrambleHeight(event.event_id, scramble) + ROW_PADDING)
    }
  }
  return height
}

function scrambleHeight(eventId: string, scramble: string): number {
  const font = scramble.length > LONG_SCRAMBLE ? SMALL : NORMAL
  const lines = scrambleLines(eventId, scramble)
    .reduce((sum, line) => sum + wrappedLines(scramblePieces(eventId, line), font.chars), 0)
  return lines * font.lineHeight
}

/** Number of lines after wrapping between pieces (moves, or "(1, -3) /" in Square-1). */
function wrappedLines(words: string[], width: number): number {
  let lines = 1
  let used = 0
  for (const word of words) {
    const needed = used === 0 ? word.length : used + 1 + word.length
    if (needed > width && used > 0) {
      lines++
      used = word.length
    } else {
      used = needed
    }
  }
  return lines
}

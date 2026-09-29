import { describe, expect, it } from 'vitest'
import { wcaEvents } from 'cubing/puzzles'
import { EVENT_IDS } from './events'
import { scrambleLines, scramblePieces } from './scramble'

describe('scrambleLines', () => {
  const minx = [
    "R-- D-- R-- D++ R-- D++ R-- D-- R-- D++ U",
    "R++ D-- R-- D++ R-- D-- R++ D++ R-- D++ U'",
    "R-- D-- R++ D++ R++ D-- R-- D++ R++ D++ U",
  ]

  it('splits a megaminx scramble stored in one line', () => {
    expect(scrambleLines('minx', minx.join(' '))).toEqual(minx)
  })

  it('keeps the lines of a scramble from cubing.js', () => {
    expect(scrambleLines('minx', minx.join('\n'))).toEqual(minx)
  })

  it('other events are one line', () => {
    expect(scrambleLines('777', "3Rw2 3Fw2\nL  Fw ")).toEqual(['3Rw2 3Fw2 L Fw'])
    expect(scrambleLines('sq1', '(-2, 0) / (0, -3) /')).toEqual(['(-2, 0) / (0, -3) /'])
  })
})

describe('scramblePieces', () => {
  it('a Square-1 line is split right after each slash', () => {
    expect(scramblePieces('sq1', '(-2, 0) / (0, -3) / (-4, 2)')).toEqual(['(-2, 0) /', '(0, -3) /', '(-4, 2)'])
    expect(scramblePieces('sq1', '(1, 0) / (-1, -1) /')).toEqual(['(1, 0) /', '(-1, -1) /'])
  })

  it('other events are split into moves', () => {
    expect(scramblePieces('777', '3Rw2 3Fw2 L Fw')).toEqual(['3Rw2', '3Fw2', 'L', 'Fw'])
  })
})

describe('events', () => {
  it('every event is a WCA event known to cubing.js', () => {
    for (const eventId of EVENT_IDS) {
      expect(wcaEvents).toHaveProperty(eventId)
    }
  })
})

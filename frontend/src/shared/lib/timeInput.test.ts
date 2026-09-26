// Parsing is only on the frontend (the server receives integers),
// but its cases are kept with the others in testdata/results_cases.json.
import { describe, expect, it } from 'vitest'
import cases from '../../../../testdata/results_cases.json'
import { parseTimeInput } from './timeInput'

describe('parseTimeInput', () => {
  it.each(cases.parseTimeInput)('"$text" → $expected', (c) => {
    expect(parseTimeInput(c.text)).toBe(c.expected)
  })
})

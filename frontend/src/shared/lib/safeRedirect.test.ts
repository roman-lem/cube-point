import { describe, expect, it } from 'vitest'
import { safeRedirect } from './safeRedirect'

describe('safeRedirect', () => {
  it.each(['/', '/club/1', '/records?event=333#top'])('accepts the internal path %s', (path) => {
    expect(safeRedirect(path)).toBe(path)
  })

  it.each([
    undefined,
    null,
    ['/club'],
    '',
    'club',
    'https://evil.com',
    '//evil.com',
    '/\\evil.com',
    'javascript:alert(1)',
  ])('replaces %s with the default path', (value) => {
    expect(safeRedirect(value)).toBe('/')
    expect(safeRedirect(value, '/login')).toBe('/login')
  })
})

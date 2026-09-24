import { describe, expect, it } from 'vitest'
import { safeRedirect } from './safeRedirect'

describe('safeRedirect', () => {
  it.each(['/', '/club/1', '/records?event=333#top'])('пропускает внутренний путь %s', (path) => {
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
  ])('заменяет %s на адрес по умолчанию', (value) => {
    expect(safeRedirect(value)).toBe('/')
    expect(safeRedirect(value, '/login')).toBe('/login')
  })
})

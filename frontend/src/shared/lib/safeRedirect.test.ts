import { describe, expect, it } from 'vitest'
import { safeRedirect } from './safeRedirect'

describe('safeRedirect', () => {
  it.each(['/', '/club/1', '/records?event=333#top', '/consents', '/timer?q=%20a'])(
    'accepts the internal path %s',
    (path) => {
      expect(safeRedirect(path)).toBe(path)
    },
  )

  it.each([
    undefined,
    null,
    ['/club'],
    '',
    'club',
    'https://evil.com',
    '//evil.com',
    '/\\evil.com',
    '/club\\..\\evil',
    '/\t/evil.com',
    '/\n/evil.com',
    '/ /evil.com',
    'javascript:alert(1)',
  ])('replaces %s with the default path', (value) => {
    expect(safeRedirect(value)).toBe('/')
    expect(safeRedirect(value, '/login')).toBe('/login')
  })

  it('takes the redirect of a forced page instead of the page', () => {
    expect(safeRedirect('/consent?redirect=%2Ftimer%3Fevent%3D333')).toBe('/timer?event=333')
    expect(safeRedirect('/change-password?redirect=/clubs/1')).toBe('/clubs/1')
  })

  it('unwraps a nested redirect', () => {
    const nested = '/consent?redirect=' + encodeURIComponent(
      '/change-password?redirect=' + encodeURIComponent('/consent?redirect=/timer'),
    )
    expect(safeRedirect(nested)).toBe('/timer')
  })

  it.each(['/Consent/?redirect=/timer', '/CHANGE-PASSWORD?redirect=/timer'])(
    'recognizes the forced page %s in another case and with a slash',
    (path) => {
      expect(safeRedirect(path)).toBe('/timer')
    },
  )

  it.each([
    '/consent',
    '/change-password?redirect=/consent',
    '/consent?redirect=//evil.com',
    '/consent?redirect=https://evil.com',
  ])('gives the default path for %s', (path) => {
    expect(safeRedirect(path)).toBe('/')
  })
})

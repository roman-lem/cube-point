import { describe, expect, it } from 'vitest'
import { forcedRedirect } from './forcedPage'

const OK = { must_change_password: false, consents_required: false }
const PASSWORD = { must_change_password: true, consents_required: false }
const CONSENTS = { must_change_password: false, consents_required: true }
const BOTH = { must_change_password: true, consents_required: true }

const route = (name: string, fullPath: string) => ({ name, fullPath })
const timer = route('timer', '/timer?event=333')

describe('forcedRedirect', () => {
  it('lets a guest and a user without requirements through', () => {
    expect(forcedRedirect(null, timer)).toBeNull()
    expect(forcedRedirect(OK, timer)).toBeNull()
  })

  it('sends to the password change with the original page', () => {
    expect(forcedRedirect(PASSWORD, timer)).toEqual({
      name: 'change-password', query: { redirect: '/timer?event=333' },
    })
  })

  it('sends to the consents with the original page', () => {
    expect(forcedRedirect(CONSENTS, timer)).toEqual({
      name: 'consent', query: { redirect: '/timer?event=333' },
    })
  })

  it('does not navigate again from the forced page itself', () => {
    expect(forcedRedirect(CONSENTS, route('consent', '/consent?redirect=/timer'))).toBeNull()
    expect(forcedRedirect(PASSWORD, route('change-password', '/change-password'))).toBeNull()
  })

  it('opens the consent texts while consents are missing', () => {
    expect(forcedRedirect(CONSENTS, route('privacy', '/privacy#processing'))).toBeNull()
    expect(forcedRedirect(CONSENTS, route('publication-consent', '/publication-consent')))
      .toBeNull()
  })

  it('goes through both pages in turn and keeps the original page', () => {
    // The password comes first.
    const first = forcedRedirect(BOTH, timer)
    expect(first).toEqual({ name: 'change-password', query: { redirect: '/timer?event=333' } })

    // The password is changed: the page redirects to the original one, and the guard
    // sends to the consents with the same original page.
    const second = forcedRedirect(CONSENTS, timer)
    expect(second).toEqual({ name: 'consent', query: { redirect: '/timer?event=333' } })

    // Consents given: the original page opens.
    expect(forcedRedirect(OK, timer)).toBeNull()
  })

  it('moves from the consent page to the password change without nesting', () => {
    const consent = route('consent', '/consent?redirect=%2Ftimer%3Fevent%3D333')
    expect(forcedRedirect(BOTH, consent)).toEqual({
      name: 'change-password', query: { redirect: '/timer?event=333' },
    })
  })

  it('never puts a forced page into the redirect', () => {
    expect(forcedRedirect(PASSWORD, route('consent', '/consent'))).toEqual({
      name: 'change-password', query: {},
    })
    const nested = route('consent', '/consent?redirect=' + encodeURIComponent('/consent?redirect=/clubs/1'))
    expect(forcedRedirect(PASSWORD, nested)).toEqual({
      name: 'change-password', query: { redirect: '/clubs/1' },
    })
  })
})

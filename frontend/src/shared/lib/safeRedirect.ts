/**
 * Pages the app forces the user to (temporary password change, consents, see
 * app/router/forcedPage.ts). They are never a destination: their own ?redirect= is taken
 * instead. vue-router matches them regardless of case and a trailing slash.
 */
const FORCED_PATHS = ['/change-password', '/consent']

/**
 * Where to go after login or a forced page, from ?redirect=…
 *
 * Only paths within the site are accepted: "/…", but not "//evil.com"
 * and not "/\evil.com" (the browser treats both as another site). Backslashes,
 * spaces and control characters are rejected anywhere: the browser drops tabs
 * and line breaks, and "/\t/evil.com" would become "//evil.com". A real path
 * from the router has them percent-encoded.
 * A forced page is replaced by its own redirect, so the result is never one.
 */
export function safeRedirect(value: unknown, fallback = '/'): string {
  let path = value
  // Each step takes the redirect inside the previous path, so the loop ends.
  for (;;) {
    if (
      typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//') ||
      /[\\\s\x00-\x1f\x7f]/.test(path)
    ) {
      return fallback
    }
    const url = new URL(path, 'http://site')
    const pathname = url.pathname.toLowerCase().replace(/\/+$/, '')
    if (!FORCED_PATHS.includes(pathname)) {
      return path
    }
    path = url.searchParams.get('redirect')
  }
}

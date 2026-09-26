/**
 * Where to go after login, from ?redirect=…
 *
 * Only paths within the site are accepted: "/…", but not "//evil.com"
 * and not "/\evil.com" (the browser treats both as another site).
 */
export function safeRedirect(value: unknown, fallback = '/'): string {
  if (typeof value !== 'string' || !value.startsWith('/')) {
    return fallback
  }
  if (value.startsWith('//') || value.startsWith('/\\')) {
    return fallback
  }
  return value
}

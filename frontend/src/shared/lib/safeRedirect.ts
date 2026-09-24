/**
 * Адрес для перехода после входа из ?redirect=…
 *
 * Принимаются только пути внутри сайта: "/…", но не "//evil.com"
 * и не "/\evil.com" (браузер считает оба адресом другого сайта).
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

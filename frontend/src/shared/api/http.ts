// HTTP client for /api: JSON, session cookies, CSRF token and a uniform error format.
//
// Server error: { error: { code, message, fields?, ...data } },
// see backend/app/errors.py.

export type FieldErrors = Record<string, string>

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    /** Errors under form fields, validation_error only. */
    readonly fields: FieldErrors = {},
    /** Other error fields: fresh data on a conflict, retry_after, etc. */
    readonly data: Record<string, unknown> = {},
  ) {
    super(message)
  }
}

type Handler = () => void

let unauthorizedHandler: Handler | null = null
let passwordChangeHandler: Handler | null = null
let consentsHandler: Handler | null = null

/** Called when there is no session or it was revoked (401 unauthorized). */
export function onUnauthorized(handler: Handler) {
  unauthorizedHandler = handler
}

/** Called when the server requires changing the temporary password. */
export function onPasswordChangeRequired(handler: Handler) {
  passwordChangeHandler = handler
}

/** Called when the server requires consents to data processing. */
export function onConsentsRequired(handler: Handler) {
  consentsHandler = handler
}

// The token is bound to the session and lives as long as it does. It is requested on the first
// modifying request and reloaded if the server rejected it.
let csrfToken: string | null = null

async function getCsrfToken(): Promise<string> {
  if (!csrfToken) {
    const data = await request<{ csrf_token: string }>('GET', '/api/auth/csrf')
    csrfToken = data.csrf_token
  }
  return csrfToken
}

async function request<T>(method: string, url: string, body?: unknown, retryCsrf = true): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (method !== 'GET') {
    headers['X-CSRFToken'] = await getCsrfToken()
  }

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'network_error', 'Нет связи с сервером')
  }

  if (response.ok) {
    return (response.status === 204 ? undefined : await response.json()) as T
  }

  const error = await readError(response)
  if (error.code === 'csrf_failed' && retryCsrf) {
    csrfToken = null
    return request<T>(method, url, body, false)
  }
  if (error.code === 'unauthorized') {
    unauthorizedHandler?.()
  }
  if (error.code === 'password_change_required') {
    passwordChangeHandler?.()
  }
  if (error.code === 'consents_required') {
    consentsHandler?.()
  }
  throw error
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const { error } = await response.json()
    const { code, message, fields, ...data } = error
    return new ApiError(response.status, code, message, fields, data)
  } catch {
    // The response is not from our API (e.g. 502 from nginx).
    return new ApiError(response.status, 'http_error', 'Ошибка сервера, попробуйте ещё раз')
  }
}

export const http = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body?: unknown) => request<T>('POST', url, body),
  put: <T>(url: string, body?: unknown) => request<T>('PUT', url, body),
  patch: <T>(url: string, body?: unknown) => request<T>('PATCH', url, body),
  delete: <T>(url: string, body?: unknown) => request<T>('DELETE', url, body),
}

// HTTP-клиент для /api: JSON, куки сессии, CSRF-токен и единый формат ошибок.
//
// Ошибка сервера: { error: { code, message, fields?, retry_after? } },
// см. backend/app/errors.py.

export type FieldErrors = Record<string, string>

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    /** Ошибки под полями формы, только у validation_error. */
    readonly fields: FieldErrors = {},
  ) {
    super(message)
  }
}

type Handler = () => void

let unauthorizedHandler: Handler | null = null
let passwordChangeHandler: Handler | null = null

/** Вызывается, когда сессии нет или она отозвана (401 unauthorized). */
export function onUnauthorized(handler: Handler) {
  unauthorizedHandler = handler
}

/** Вызывается, когда сервер требует сменить временный пароль. */
export function onPasswordChangeRequired(handler: Handler) {
  passwordChangeHandler = handler
}

// Токен привязан к сессии и живёт вместе с ней. Запрашиваем его при первом
// изменяющем запросе, а если сервер его отклонил — перечитываем.
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
  throw error
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const { error } = await response.json()
    return new ApiError(response.status, error.code, error.message, error.fields)
  } catch {
    // Ответ не от нашего API (например, 502 от nginx).
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

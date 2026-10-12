/** Thin fetch wrapper for /api/v1 (docs/API_SPECIFICATION.md §1). */

export const API_BASE = '/api/v1'

/** The server answered with an RFC 9457 problem; `code` is the stable error code. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryAfterSeconds: number | undefined

  constructor(status: number, code: string, retryAfterSeconds?: number) {
    super(code)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfterSeconds = retryAfterSeconds
  }
}

/** The request never got an answer (offline, connection dropped). */
export class NetworkError extends Error {
  constructor() {
    super('network_error')
    this.name = 'NetworkError'
  }
}

/** Worth trying again later without changing anything. */
export function isRetryable(error: unknown): boolean {
  if (error instanceof NetworkError) return true
  return error instanceof ApiError && (error.status === 429 || error.status >= 500)
}

export function errorCode(error: unknown): string {
  if (error instanceof ApiError) return error.code
  if (error instanceof NetworkError) return 'network_error'
  return 'unexpected_error'
}

// Kept in memory only: it comes back from /auth/me after a reload.
let csrfToken: string | null = null

export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

export interface RequestOptions {
  json?: unknown
  form?: FormData
  headers?: Record<string, string>
}

export async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE',
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json', ...options.headers }
  if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken
  let body: BodyInit | undefined
  if (options.json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.json)
  } else if (options.form) {
    body = options.form // the browser sets the multipart boundary
  }

  let response: Response
  try {
    response = await fetch(API_BASE + path, { method, headers, body, credentials: 'same-origin' })
  } catch {
    throw new NetworkError()
  }
  if (response.status === 204) return undefined as T
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const code =
      data && typeof data === 'object' && 'code' in data && typeof data.code === 'string'
        ? data.code
        : `http_${response.status}`
    const retryAfter = Number(response.headers.get('Retry-After'))
    throw new ApiError(response.status, code, retryAfter > 0 ? retryAfter : undefined)
  }
  return data as T
}

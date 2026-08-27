import type { TokenPair } from './types'

const ACCESS = 'csp.access_token'

type AccessTokenResponse = {
  access_token: string
  token_type: string
}

export function tokenPair(): TokenPair | null {
  const access_token = sessionStorage.getItem(ACCESS)
  return access_token ? { access_token, refresh_token: '' } : null
}

export function saveTokens(tokens: Pick<TokenPair, 'access_token'>) {
  sessionStorage.setItem(ACCESS, tokens.access_token)
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS)
}

async function refreshTokens(): Promise<boolean> {
  const response = await fetch('/api/v1/auth/browser/refresh', {
    method: 'POST',
    credentials: 'same-origin',
  })
  if (!response.ok) return false
  const tokens = (await response.json()) as AccessTokenResponse
  saveTokens(tokens)
  return true
}

async function parseError(response: Response): Promise<Error> {
  let detail = `${response.status} ${response.statusText}`
  try {
    const body = (await response.json()) as { detail?: string }
    if (body.detail) detail = body.detail
  } catch {
    // Preserve HTTP status if the response is not JSON.
  }
  return new Error(detail)
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  let requestPath = path
  let requestInit = init

  if (path === '/api/v1/auth/login') {
    requestPath = '/api/v1/auth/browser/login'
  } else if (path === '/api/v1/auth/logout') {
    requestPath = '/api/v1/auth/browser/logout'
    requestInit = { method: 'POST' }
  }

  const access = sessionStorage.getItem(ACCESS)
  const headers = new Headers(requestInit.headers)
  if (!headers.has('Content-Type') && requestInit.body) headers.set('Content-Type', 'application/json')
  if (access) headers.set('Authorization', `Bearer ${access}`)

  const response = await fetch(requestPath, {
    ...requestInit,
    headers,
    credentials: 'same-origin',
  })

  if (response.status === 401 && retry && requestPath !== '/api/v1/auth/browser/login') {
    if (await refreshTokens()) return api<T>(path, init, false)
  }
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

import type { TokenPair } from './types'

const ACCESS = 'csp.access_token'
const REFRESH = 'csp.refresh_token'

export function tokenPair(): TokenPair | null {
  const access_token = sessionStorage.getItem(ACCESS)
  const refresh_token = sessionStorage.getItem(REFRESH)
  return access_token && refresh_token ? { access_token, refresh_token } : null
}

export function saveTokens(tokens: TokenPair) {
  sessionStorage.setItem(ACCESS, tokens.access_token)
  sessionStorage.setItem(REFRESH, tokens.refresh_token)
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS)
  sessionStorage.removeItem(REFRESH)
}

async function refreshTokens(): Promise<boolean> {
  const refresh_token = sessionStorage.getItem(REFRESH)
  if (!refresh_token) return false
  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token }),
  })
  if (!response.ok) return false
  saveTokens((await response.json()) as TokenPair)
  return true
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const access = sessionStorage.getItem(ACCESS)
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json')
  if (access) headers.set('Authorization', `Bearer ${access}`)
  const response = await fetch(path, { ...init, headers })
  if (response.status === 401 && retry && (await refreshTokens())) return api<T>(path, init, false)
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Preserve HTTP status if the response is not JSON.
    }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

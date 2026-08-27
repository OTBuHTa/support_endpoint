const ACCESS = 'csp.access_token'

type AccessTokenResponse = {
  access_token: string
  token_type: string
}

export function hasAccessToken(): boolean {
  return Boolean(sessionStorage.getItem(ACCESS))
}

export function saveAccessToken(accessToken: string) {
  sessionStorage.setItem(ACCESS, accessToken)
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
  saveAccessToken(tokens.access_token)
  return true
}

export async function browserLogin(email: string, password: string): Promise<void> {
  const response = await fetch('/api/v1/auth/browser/login', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
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
  const tokens = (await response.json()) as AccessTokenResponse
  saveAccessToken(tokens.access_token)
}

export async function browserLogout(): Promise<void> {
  try {
    await fetch('/api/v1/auth/browser/logout', {
      method: 'POST',
      credentials: 'same-origin',
    })
  } finally {
    clearTokens()
  }
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const access = sessionStorage.getItem(ACCESS)
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json')
  if (access) headers.set('Authorization', `Bearer ${access}`)
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin' })
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

const TOKEN_KEY = 'ktm.token'
const USER_KEY = 'ktm.user'

// Standalone from AuthContext so the axios interceptor can read/clear auth
// without importing React state (and without a circular import).

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    // A corrupted entry should log the session out, not crash the app on boot.
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function storeAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

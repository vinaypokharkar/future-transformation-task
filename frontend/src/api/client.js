import axios from 'axios'
import { clearAuth, getToken } from './authStorage'

const LOGIN_PATH = '/auth/login'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// AuthContext registers a handler so a 401 can clear React state and navigate,
// rather than this module hard-reloading the page.
let onUnauthorized = null

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes(LOGIN_PATH)

    // Skipping the login request is load-bearing: without it a wrong password
    // triggers the session-expired redirect instead of an inline error.
    if (error.response?.status === 401 && !isLoginRequest) {
      clearAuth()
      onUnauthorized?.()
    }
    return Promise.reject(error)
  },
)

/** Unwraps FastAPI's `{"detail": "..."}` error shape into a displayable string. */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  // 422 returns a list of validation objects rather than a string.
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item.msg).filter(Boolean).join(', ') || fallback
  }
  if (error?.code === 'ERR_NETWORK') return 'Cannot reach the server. Is the backend running?'
  return fallback
}

export default api

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { login as loginRequest } from '../api/auth'
import { clearAuth, getStoredUser, getToken, storeAuth } from '../api/authStorage'
import { setUnauthorizedHandler } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  // Initialised straight from localStorage so a refresh keeps the session
  // without a flash of the login page.
  const [token, setToken] = useState(() => getToken())
  const [user, setUser] = useState(() => getStoredUser())
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const logout = useCallback(() => {
    clearAuth()
    setToken(null)
    setUser(null)
    // Without this, the next user to log in briefly sees the previous one's cached data.
    queryClient.clear()
    navigate('/login', { replace: true })
  }, [navigate, queryClient])

  // Lets the axios 401 interceptor tear down the session through React
  // instead of hard-reloading the page.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null)
      setUser(null)
      queryClient.clear()
      navigate('/login', { replace: true })
    })
    return () => setUnauthorizedHandler(null)
  }, [navigate, queryClient])

  const login = useCallback(async (email, password) => {
    const data = await loginRequest(email, password)
    storeAuth(data.access_token, data.user)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const value = useMemo(
    () => ({
      token,
      user,
      login,
      logout,
      isAuthenticated: Boolean(token),
      isAdmin: user?.role === 'admin',
    }),
    [token, user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

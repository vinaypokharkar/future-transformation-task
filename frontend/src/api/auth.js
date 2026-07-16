import api from './client'

export async function login(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  return data
}

export async function fetchCurrentUser() {
  const { data } = await api.get('/auth/me')
  return data
}

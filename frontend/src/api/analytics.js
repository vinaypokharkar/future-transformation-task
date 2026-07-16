import api from './client'

/** Admin only. */
export async function fetchAnalytics() {
  const { data } = await api.get('/analytics')
  return data
}

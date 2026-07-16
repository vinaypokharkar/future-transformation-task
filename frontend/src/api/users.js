import api from './client'

/** Admin only — backs the assignee dropdowns on the Tasks page. */
export async function listUsers() {
  const { data } = await api.get('/users')
  return data
}

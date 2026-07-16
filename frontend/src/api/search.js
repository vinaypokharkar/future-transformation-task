import api from './client'

export async function search(query, k) {
  const { data } = await api.post('/search', k ? { query, k } : { query })
  return data
}

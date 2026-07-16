import api from './client'

function compact(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  )
}

export async function listDocuments(filters = {}) {
  const { data } = await api.get('/documents', { params: compact(filters) })
  return data
}

export async function fetchDocument(id) {
  const { data } = await api.get(`/documents/${id}`)
  return data
}

/**
 * Admin only. Content-Type is deliberately NOT set: axios must derive the
 * multipart boundary from the FormData itself, and setting it by hand
 * produces a boundary-less header the server cannot parse.
 */
export async function uploadDocument(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const { data } = await api.post('/documents', formData, {
    onUploadProgress: (event) => {
      if (!onProgress || !event.total) return
      onProgress(Math.round((event.loaded * 100) / event.total))
    },
  })
  return data
}

/** Admin only. */
export async function deleteDocument(id) {
  await api.delete(`/documents/${id}`)
}

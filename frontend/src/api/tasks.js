import api from './client'

/**
 * Drops empty filter values so the request sends `?status=completed` rather than
 * `?status=&assigned_to=`, which the backend would reject as a validation error.
 */
function compact(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  )
}

export async function listTasks(filters = {}) {
  const { data } = await api.get('/tasks', { params: compact(filters) })
  return data
}

export async function fetchTask(id) {
  const { data } = await api.get(`/tasks/${id}`)
  return data
}

/** Admin only. */
export async function createTask(payload) {
  const { data } = await api.post('/tasks', compact(payload))
  return data
}

/**
 * Update one assignee's status.
 *
 * Status is per-assignee, so this always resolves to exactly one person.
 * Omitting userId updates the caller's own. Passing one is admin-only — the
 * server rejects it for everybody else, so this is convenience, not a
 * permission check.
 */
export async function updateTaskStatus(id, status, userId) {
  const { data } = await api.patch(
    `/tasks/${id}/status`,
    compact({ status, user_id: userId }),
  )
  return data
}
